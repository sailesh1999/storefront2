from django.db.models import fields
from django.db import transaction
from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField

from store.models import Cart, CartItem, Customer, Order, OrderItem, Product, Collection, Review
from store.signals import order_created

# NORMAL SERIALIZERS

# class CollectionSerializer(serializers.Serializer):
#     id = serializers.IntegerField()
#     title = serializers.CharField(max_length=255)

# class ProductSerializer(serializers.Serializer):
#     # Deliberately show only few fields from Product model to clients.
#     # Read only is true because when deserializing we won't receive ID from client. 
#     id = serializers.IntegerField(read_only=True)
#     title = serializers.CharField(max_length=255)

#     # We can change name different from internal representation (Product model). This maps unit_price in Product object to price.
    # price = serializers.DecimalField(max_digits=6,decimal_places=2,source='unit_price')

#     # Show fields that are not in Product model.
#     price_with_tax = serializers.SerializerMethodField()
#     # prefix method name with "get_". Alternatively you can give method_name argument to SerializerMethodField.
#     def get_price_with_tax(self,product:Product):
#         return product.unit_price * Decimal(1.1)


#     # Serializer related fields.
    
#     # 1) Primary key of related field. 
#     # During deserialization, if we pass collection id, DRF automatically gets corresponding collection and puts that in validated_data.
#     collection = serializers.PrimaryKeyRelatedField(queryset = Collection.objects.all())
#     # OR. Below one doesn't work for de-serialization.
#     # collection = serializers.IntegerField(source='collection_id')

#     # 2) String representation of related field. Make sure you already queried collection along with product using "select_related".
#     # collection = serializers.StringRelatedField()

#     # 3) Nested object representation
#     # collection = CollectionSerializer()

#     # 4) Hyperlink related field
#     # collection = serializers.HyperlinkedRelatedField(queryset=Collection.objects.all(),view_name='collection-detail')


# MODEL SERIALIZERS

class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id','title','products_count']

    products_count = serializers.SerializerMethodField()
    def get_products_count(self,collection: Collection):
        return collection.products.count()

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        # If field is present in Model, then it takes it from there. Else, it takes the field from this class's fields (written below).
        fields=['id','title','slug','description','unit_price','price_with_tax','collection','inventory']
    
    # price = serializers.DecimalField(max_digits=6,decimal_places=2,source='unit_price')
    slug = serializers.SlugField(read_only=True)

    price_with_tax = serializers.SerializerMethodField()
    def get_price_with_tax(self,product:Product):
        return product.unit_price * Decimal(1.1)

    # collection = serializers.HyperlinkedRelatedField(queryset=Collection.objects.all(),view_name='collection-detail')

    # # If we want to have some extra custom validations, we can use this method.
    # def validate(self, data):
    #     if data['password'] != data['confirm_password']:
    #         return ValidationError('Passwords are not matching')
    #     return data
    
    # save method calls one of the 'create' or 'update' method depending on state of the serializer
    def create(self, validated_data):
        product:Product = Product(**validated_data)
        title:str = product.title
        product.slug = title.replace(" ","-")
        product.save()
        return product

    def update(self,instance,validated_data):
        for key in validated_data:
            instance.key = validated_data[key]
        if "title" in validated_data:
            instance.slug = validated_data['title'].replace(" ","-")
        instance.save()
        return instance

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id','date','name','description']

    def create(self, validated_data):
        product_id = self.context['product_id']
        review = Review.objects.create(product_id=product_id,**validated_data)
        return review

class SimpleProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id','title','unit_price']

class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        if not Product.objects.filter(id = value).exists():
            raise serializers.ValidationError('No product with the given product ID exists')
        return value

    class Meta:
        model = CartItem
        fields = ['id','product_id','quantity']

    def save(self, **kwargs):
        cart_id = self.context['cart_id']
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cart_item = CartItem.objects.get(cart_id=cart_id,product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            self.instance = CartItem.objects.create(cart_id = cart_id, **self.validated_data)
        
        return self.instance

class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['quantity']

class CartItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    total_price = SerializerMethodField()
    class Meta:
        model = CartItem
        fields = ['id','product','quantity','total_price']

    def get_total_price(self,cart_item:CartItem):
        return cart_item.product.unit_price * cart_item.quantity
        
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True,read_only=True)
    total_price = SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id', 'created_at','items','total_price']
        read_only_fields = ('id', 'created_at', 'items','total_price')
    
    def get_total_price(self,cart:Cart):
        cart_items = cart.items.all()
        return sum([item.quantity * item.product.unit_price for item in cart_items])


class CustomerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Customer
        fields=['id','user_id','phone','birth_date','membership']


class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer()
    class Meta:
        model = OrderItem
        fields=['id','product','quantity','unit_price']


class OrderSerializer(serializers.ModelSerializer):
    orderitem_set = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields=['id','placed_at','payment_status','customer','orderitem_set']

class UpdateOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields=['id','payment_status']


class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField()

    def validate_cart_id(self,cart_id):
        if not Cart.objects.filter(pk=cart_id).exists():
            raise ValidationError("No cart with given ID exists")
        if not CartItem.objects.filter(cart_id=cart_id).exists():
            raise ValidationError("Cart is empty")
        return cart_id


    def save(self, **kwargs):
        with transaction.atomic():
            cart_id = self.validated_data['cart_id']
            user_id = self.context['user_id']

            customer = Customer.objects.get(user_id=user_id)
            order = Order.objects.create(customer=customer)

            cart_items_qs = CartItem.objects.select_related('product').filter(cart_id=cart_id)

            order_items = [
                OrderItem(
                    order = order, product = cart_item.product, quantity = cart_item.quantity, unit_price = cart_item.product.unit_price
                ) for cart_item in cart_items_qs
            ]

            OrderItem.objects.bulk_create(order_items)

            Cart.objects.filter(id=cart_id).delete()

            # Sending custom signal (order is created)
            order_created.send_robust(sender=self.__class__, order=order)
            
            return order
            