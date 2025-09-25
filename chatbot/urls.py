from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('response/', views.chatbot_response, name='chatbot_response'),
]
