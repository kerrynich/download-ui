from django.urls import path

from .views import (DownloadCreateView, DownloadDeleteView, DownloadListView,
                    DownloadDetailView, DownloadProgressView, DownloadUpdateView, DownloadHomeView)

app_name = 'download'
urlpatterns = [
    path('', DownloadHomeView.as_view(), name='home'),
    path('create/', DownloadCreateView.as_view(), name='create'),
    path('<int:pk>/', DownloadDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', DownloadUpdateView.as_view(), name='update'),
    path('list/', DownloadListView.as_view(), name='list'),
    path('<int:pk>/delete/', DownloadDeleteView.as_view(), name='delete'),
    path('<int:pk>/progress/', DownloadProgressView.as_view(), name='progress')
]
