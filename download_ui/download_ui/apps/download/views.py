from datetime import timedelta
import logging

from celery.result import AsyncResult
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.views.generic import CreateView, DeleteView, ListView, DetailView, UpdateView, View

from .forms import DownloadForm, DownloadFormatForm
from .models import Download
from .tasks import worker_download

logger = logging.getLogger('__name__')


class DownloadHomeView(View):
    def get(self, request):
        time_threshold = timezone.now() - timedelta(hours=24)
        downloads = Download.objects.filter(
            created_at__gte=time_threshold).exclude(status=Download.Status.DRAFT)
        context = {'downloads': downloads}
        return render(request, "download_home.html", context)


class DownloadCreateView(CreateView):
    form_class = DownloadForm
    template_name = "partials/download_form.html"

    def get_success_url(self):
        logger.debug('Initial form submitted. ID is %d', self.object.id)
        return reverse_lazy('download:update', kwargs={'pk': self.object.id})

    def form_invalid(self, form):
        context = {'form': form}
        return render(self.request, "partials/download_form.html", context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'old_pk' in self.request.GET:
            down_object = self.get_object()
            info = {'percent_str': '0.0%', 'percent': 0}
            context['download'] = down_object
            context['task_info'] = info
            context['trigger'] = 'load delay:600ms'
        return context

    def get_object(self, *args, **kwargs):
        download = get_object_or_404(Download, pk=self.request.GET['old_pk'])
        return download


class DownloadUpdateView(UpdateView):
    form_class = DownloadFormatForm
    model = Download
    template_name = "partials/download_format_form.html"

    def get_success_url(self):
        logger.debug('Final form submitted. ID is %d', self.object.id)
        query_kwargs = {'old_pk': self.object.id}
        og_url = reverse_lazy('download:create')
        return f'{og_url}?{urlencode(query_kwargs)}'

    def form_valid(self, form):
        response = super().form_valid(form)
        worker_download.delay(
            self.object.url,
            self.object.pk,
            self.object.command.name,
            self.object.file_format.format_code
        )
        return response

    def form_invalid(self, form):
        super().form_invalid(form)
        logger.debug('Update form was invalid')
        context = {'form': form}
        return render(self.request, "partials/download_format_form.html", context)

    def get_initial(self):
        initial = super().get_initial()
        # Adding ID to initial data so form can query with it
        down_object = self.get_object()
        initial['id'] = down_object.id
        return initial

    def get_object(self, *args, **kwargs):
        download = get_object_or_404(Download, pk=self.kwargs['pk'])
        return download


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


class DownloadProgressView(View):
    def get(self, request, pk):
        download = Download.objects.get(pk=pk)
        if download.status == Download.Status.STARTED:
            task = AsyncResult(download.active_task_id)
            context = {
                'task_status': task.status,
                'task_id': task.id,
                'task_info': task.info,
                'download': download,
                'trigger': 'load delay:600ms'
            }
        else:
            context = {'download': download, 'trigger': 'none'}

        return render(request, "partials/download_progress.html", context)
