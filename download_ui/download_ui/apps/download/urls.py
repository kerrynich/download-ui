from django.urls import path

from .views import (DownloadCreateView, DownloadArchiveView, DownloadListView, DownloadCancelView,
                    DownloadDetailView, DownloadProgressView, DownloadUpdateView, DownloadHomeView,
                    RegisterView)

app_name = 'download'
urlpatterns = [
    path('', DownloadHomeView.as_view(), name='home'),
    path('create/', DownloadCreateView.as_view(), name='create'),
    path('<int:pk>/', DownloadDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', DownloadUpdateView.as_view(), name='update'),
    path('list/', DownloadListView.as_view(), name='list'),
    path('<int:pk>/archive/', DownloadArchiveView.as_view(), name='archive'),
    path('<int:pk>/cancel/', DownloadCancelView.as_view(), name='cancel'),
    path('<int:pk>/progress/', DownloadProgressView.as_view(), name='progress'),
    path('register/', RegisterView.as_view(), name="register")
]
