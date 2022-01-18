from django.db.models.query import QuerySet
from django.http import request
from django.shortcuts import render,get_object_or_404
from rest_framework import permissions

from rest_framework.decorators import api_view,action, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.mixins import ListModelMixin,CreateModelMixin,UpdateModelMixin,DestroyModelMixin,RetrieveModelMixin
from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveDestroyAPIView,RetrieveUpdateDestroyAPIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import OR, IsAdminUser, IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend

from store.filters import ProductFilter
from store.pagination import DefaultPagination
from store.permissions import IsAdminOrReadOnly
from store.serializers import AddCartItemSerializer, CartItemSerializer, CartSerializer, CollectionSerializer, CreateOrderSerializer, CustomerSerializer, OrderSerializer, ProductSerializer, ReviewSerializer, SimpleProductSerializer, UpdateCartItemSerializer, UpdateOrderSerializer
from .models import Cart, CartItem, Collection, Customer, Order, OrderItem, Product, Review

class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    # Filtering using django_filters library
    filter_backends = [DjangoFilterBackend,SearchFilter,OrderingFilter]
    filterset_class = ProductFilter
    pagination_class = DefaultPagination
    search_fields = ['title','description']
    ordering_fields = ['unit_price','last_update']
    permission_classes = [IsAdminOrReadOnly]

    
    def get_serializer_context(self):
        return {'request',self.request}

    def destroy(self, request, *args, **kwargs):
        if OrderItem.objects.filter(product_id=kwargs['pk']).exists():
            return Response({'error':'Cannot delete product as it has order items associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)


class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    permission_classes = [IsAdminOrReadOnly]

    def destroy(self, request, *args, **kwargs):
        if Product.objects.filter(collection_id=kwargs['pk']).exists():
            return Response({'error':'Cannot delete collection as it has products associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super().destroy(request, *args, **kwargs)


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(product_id = self.kwargs['product_pk'])

    def get_serializer_context(self):
        return {'product_id': self.kwargs['product_pk']}


class CartViewSet(CreateModelMixin,RetrieveModelMixin,DestroyModelMixin,GenericViewSet):
    queryset = Cart.objects.prefetch_related('items','items__product').all()
    serializer_class = CartSerializer

class CartItemViewSet(ModelViewSet):
    http_method_names = ['get','post','patch','delete']
    def get_queryset(self):
        return CartItem.objects.select_related('product').filter(cart_id = self.kwargs['cart_pk'])

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    @action(detail=False,methods=['GET','PUT'],permission_classes=[IsAuthenticated])
    def me(self,request):
        customer = Customer.objects.get(id=request.user.id)
        if request.method == 'GET':
            serializer = self.serializer_class(customer)
        elif request.method == 'PUT':
            serializer = self.serializer_class(customer,data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

class OrderViewSet(ModelViewSet):
    http_method_names = ['get','post','patch','delete','head','options']

    def get_permissions(self):
        if self.request.method in ['PUT','PATCH','DELETE']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data,context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_context(self):
        return {'user_id': self.request.user.id}
    
    def get_serializer_class(self):
        request_method_serializer_map = {
            'GET': OrderSerializer,
            'POST': CreateOrderSerializer,
            'PATCH': UpdateOrderSerializer ,
            'DELETE': OrderSerializer,
            # Not sure if serializer is actually needed for delete. Check and remove if not needed
        }
        
        serializer = request_method_serializer_map[self.request.method]
        return serializer
        
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        customer_id = Customer.objects.only('id').get(user=user)
        return Order.objects.filter(customer_id=customer_id)
        

# ------------- FUNCTION BASED VIEWS ----------------- #

# # This decorator converts request to rest_framework's Request object and we can send rest_framework's Response in return
# @api_view(['GET','POST'])
# def product_list(request):
#     if request.method == 'GET':
#         products_list_qs = Product.objects.select_related('collection').all()
#         serializer = ProductSerializer(products_list_qs,many=True,context={'request':request})
#         return Response(serializer.data)
#     elif request.method == 'POST':
#         data = request.data
#         # Deserialization. Converts request to ordered dict.
#         serializer = ProductSerializer(data=data)
#         serializer.is_valid(raise_exception=True) # Before accessing validated_data, we need to check this compulsorily
#         # print(serializer.validated_data) # this will be an ordered dict
#         product=serializer.save()
#         print(product)
#         print(product.slug)
#         return Response(serializer.data,status=status.HTTP_201_CREATED)


# @api_view(['GET','PUT','DELETE'])
# def product_detail(request,id):
#     product = get_object_or_404(Product,id=id)
#     if request.method == 'GET':
#         serializer = ProductSerializer(product)
#         return Response(serializer.data)
#     elif request.method=='PUT':
#         serializer = ProductSerializer(instance=product,data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data,status=status.HTTP_200_OK)
#     elif request.method == 'DELETE':
#         if product.orderitems.count()>0:
#             return Response({'error':'Cannot delete product as it has order items associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
#         product.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)

# @api_view(['GET','POST'])
# def collection_list(request):
#     if request.method=='GET':
#         collection_list_qs = Collection.objects.all()
#         serializer = CollectionSerializer(collection_list_qs,many=True)
#         return Response(serializer.data,status=status.HTTP_200_OK)
#     elif request.method=='POST':
#         serializer = CollectionSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data,status=status.HTTP_201_CREATED)

# @api_view(['GET','PUT','DELETE'])
# def collection_detail(request,pk):
#     collection = get_object_or_404(Collection,id=pk)

#     if request.method=='GET':
#         serializer = CollectionSerializer(collection)
#         return Response(serializer.data)
    
#     elif request.method=='PUT':
#         serializer = CollectionSerializer(instance=collection,data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data,status=status.HTTP_200_OK)
    
#     elif request.method == 'DELETE':
#         if collection.products.count()>0:
#             return Response({'error':'Cannot delete colelction as it has products associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         collection.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------- CLASS BASED VIEWS (Non generic ones) --------------------- #

# class ProductList(APIView):
#     def get(self,request):
#         products_list_qs = Product.objects.select_related('collection').all()
#         serializer = ProductSerializer(products_list_qs,many=True,context={'request':request})
#         return Response(serializer.data)

#     def post(self,request):
#         data = request.data
#         # Deserialization. Converts request to ordered dict.
#         serializer = ProductSerializer(data=data)
#         serializer.is_valid(raise_exception=True) # Before accessing validated_data, we need to check this compulsorily
#         # print(serializer.validated_data) # this will be an ordered dict
#         product=serializer.save()
#         print(product)
#         print(product.slug)
#         return Response(serializer.data,status=status.HTTP_201_CREATED)


# class ProductDetail(APIView):
#     def get(self,request,id):
#         product = get_object_or_404(Product,id=id)
#         serializer = ProductSerializer(product)
#         return Response(serializer.data)
#     def put(self,request,id):
#         product = get_object_or_404(Product,id=id)
#         serializer = ProductSerializer(instance=product,data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data,status=status.HTTP_200_OK)
#     def delete(self,request,id):
#         product = get_object_or_404(Product,id=id)
#         if product.orderitems.count()>0:
#             return Response({'error':'Cannot delete product as it has order items associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
#         product.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)



# -------------------GENERIC VIEWS ----------------------- #

# class ProductList(ListCreateAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer

#     # You can use these methods incase you want to perform some logic before returning queryset or serializer class
#     # def get_queryset(self):
#     #     return Product.objects.select_related('collection').all()

#     # def get_serializer_class(self):
#     #     return ProductSerializer

#     def get_serializer_context(self):
#         return {'request',self.request}

# class ProductDetail(RetrieveUpdateDestroyAPIView):
#     queryset = Product.objects.all()
#     serializer_class = ProductSerializer
    
#     # We need to override delete method of RetrieveUpdateDestroyAPIView as we have some logic that is not common in all cases here.
#     def delete(self,request,pk):
#         product = get_object_or_404(Product,pk=pk)

#         # This is the logic that isn't common in all places.
#         if product.orderitems.count()>0:
#             return Response({'error':'Cannot delete product as it has order items associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
        
#         product.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# class CollectionList(ListCreateAPIView):
#     queryset = Collection.objects.all()
#     serializer_class = CollectionSerializer

# class CollectionDetail(RetrieveUpdateDestroyAPIView):
#     queryset = Collection.objects.all()
#     serializer_class = CollectionSerializer

#     def delete(self,request,pk):
#         collection = get_object_or_404(Collection,pk=pk)
#         if collection.products.count()>0:
#             return Response({'error':'Cannot delete collection as it has products associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         collection.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)



# ---------------FILTERING WITHOUT USING django_filters LIBRARY ------------- #

# class ProductViewSet(ModelViewSet):
#     serializer_class = ProductSerializer

#     def get_queryset(self):
#         queryset = Product.objects.all()
#         collection_id = self.request.query_params.get('collection_id')

#         if collection_id is not None:
#             queryset = queryset.filter(collection_id=collection_id)

#         return queryset

#     def get_serializer_context(self):
#         return {'request',self.request}

#     def destroy(self, request, *args, **kwargs):
#         if OrderItem.objects.filter(product_id=kwargs['pk']).exists():
#             return Response({'error':'Cannot delete product as it has order items associated with it'},status=status.HTTP_405_METHOD_NOT_ALLOWED)
#         return super().destroy(request, *args, **kwargs)



# --------------- CUSTOM RESTRICTED VIEWSET ------------- #

# class CustomerViewSet(CreateModelMixin,RetrieveModelMixin,UpdateModelMixin,GenericViewSet):
#     queryset = Customer.objects.all()
#     serializer_class = CustomerSerializer
#     permission_classes = [IsAuthenticated]

#     @action(detail=False,methods=['GET','PUT'])
#     def me(self,request):
#         customer,created = Customer.objects.get_or_create(id=request.user.id)
#         if request.method == 'GET':
#             serializer = self.serializer_class(customer)
#         elif request.method == 'PUT':
#             serializer = self.serializer_class(customer,data=request.data)
#             serializer.is_valid(raise_exception=True)
#             serializer.save()
#         return Response(serializer.data)
