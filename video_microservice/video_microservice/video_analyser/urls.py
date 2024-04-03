
from django.contrib import admin
from django.urls import path,include
from .views import *
urlpatterns = [
    path('video/<str:talentId>',VideoView.as_view(), name='video_based_scores'),
    path('test',view=test)
]