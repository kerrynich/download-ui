from django.urls import path
from .views import DownloadCreateView, DownloadDeleteView, DownloadListView, DownloadDetailView

app_name = 'download'
urlpatterns = [
    path('', DownloadCreateView.as_view(), name='create'),
    path('<int:pk>/', DownloadDetailView.as_view(), name='detail'),
    path('list/', DownloadListView.as_view(), name='list'),
    path('<int:pk>/delete/', DownloadDeleteView.as_view(), name='delete'),
]