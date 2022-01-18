
from django.contrib import admin
from django.urls import path, include
from rest_framework import urlpatterns
# from rest_framework import routers
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

router = routers.DefaultRouter()
router.register('products',views.ProductViewSet,basename='products')

products_router = routers.NestedDefaultRouter(router,'products',lookup='product')
products_router.register('reviews',views.ReviewViewSet,basename='product-reviews')
 
router.register('collections',views.CollectionViewSet)

router.register('customers',views.CustomerViewSet)


# Normally django figures out basename(the name in URL - like products for ProductViewSet) thro queryset attribute specified in viewset.
# If we don't specify this attribute in viewset, then specify basename manually here
router.register('orders',views.OrderViewSet,basename='orders')

router.register('carts',views.CartViewSet,basename='carts')

carts_router = routers.NestedDefaultRouter(router,'carts',lookup='cart')
carts_router.register('items',views.CartItemViewSet,basename='cart-items')


urlpatterns = router.urls + products_router.urls + carts_router.urls



# ----------- URL Patterns (without router module) ----------- #

# urlpatterns = [
#     # as_view() converts our class based view to regular function based view.
#     path('products/', views.ProductList.as_view()),
#     path('collections/', views.CollectionList.as_view()),
#     # <int:id> -> Converter. Accepts only int type in request.
#     path('products/<int:pk>/', views.ProductDetail.as_view()),
#     path('collections/<int:pk>/', views.CollectionDetail.as_view(),name='collection-detail'),
# ]
