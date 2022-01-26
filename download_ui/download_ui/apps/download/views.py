from django.shortcuts import render
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, DetailView
from .models import Download
from .forms import DownloadForm

def index(request):
    return HttpResponse("Hello, world. You're at the download index.")

class DownloadCreateView(CreateView):
    form_class = DownloadForm
    template_name = "download_form.html"
    success_url = reverse_lazy('download:list')

class DownloadDetailView(DetailView):
    model = Download
    template_name = "download_detail.html"

class DownloadDeleteView(DeleteView):
    model = Download
    template_name = "download_confirm_delete.html"
    success_url = reverse_lazy('download:list')

class DownloadListView(ListView):
    model = Download
    template_name = "download_list.html"
    paginate_by = 20