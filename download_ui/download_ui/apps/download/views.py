from datetime import timedelta
import logging

from celery.result import AsyncResult
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import urlencode
from django.views.generic import CreateView, ListView, DetailView, UpdateView, View

from download_ui.celery import app
from .forms import DownloadForm, DownloadFormatForm, UserRegisterForm
from .models import Download, UserProfile
from .tasks import worker_download

logger = logging.getLogger('__name__')


class DownloadHomeView(LoginRequiredMixin, View):
    def get(self, request):
        time_threshold = timezone.now() - timedelta(hours=24)
        all_downloads = Download.objects.filter(
            created_at__gte=time_threshold).exclude(
            status=Download.Status.DRAFT)
        my_downloads = all_downloads.filter(
            created_by=self.request.user)
        other_downloads = all_downloads.exclude(
            created_by=self.request.user)
        context = {
            'my_downloads': my_downloads,
            'other_downloads': other_downloads
        }
        if 'continue' in self.request.GET:
            context['continue'] = self.request.GET['continue']
        return render(request, "download_home.html", context)


class DownloadCreateView(LoginRequiredMixin, CreateView):
    form_class = DownloadForm
    template_name = "partials/download_form.html"

    def get_success_url(self):
        logger.debug('Initial form submitted. ID is %d', self.object.id)
        return reverse_lazy('download:update', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        if 'override' not in self.request.GET:
            # Get rid of dangling drafts
            existing_draft_list = Download.objects.filter(slug_id=form.instance.slug_id,
                                                          status=Download.Status.DRAFT)
            if existing_draft_list:
                for draft in existing_draft_list:
                    draft.delete()

            # See if the file has already been downloaded in any resolutions already
            existing_download_list = Download.objects.filter(slug_id=form.instance.slug_id,
                                                             status=Download.Status.COMPLETED)

            if existing_download_list:
                # Check if any of the completed downloads are actually missing
                for down in existing_download_list:
                    down.set_missing_if_file_not_found()
                    down.save()
                fresh_existing_download_list = existing_download_list.filter(
                    status=Download.Status.COMPLETED)

                # Show the modal
                if fresh_existing_download_list:
                    context = {
                        'form': form,
                        'download': form.instance,
                        'existing': fresh_existing_download_list,
                        'modal_title': 'Video Exists',
                        'modal_body': [
                            'This video has already been downloaded in the following quality(s).',
                            'Please select to skip a fresh download and use an existing file.'
                        ],
                    }
                    return render(self.request, "partials/download_form.html", context)
        form.instance.created_by = self.request.user
        return super().form_valid(form)

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


class DownloadUpdateView(LoginRequiredMixin, UpdateView):
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
        if 'override' not in self.request.GET:
            # See if the file has already been downloaded in this resolution already
            existing_download_list = Download.objects.filter(slug_id=self.object.slug_id,
                                                             status=Download.Status.COMPLETED,
                                                             file_format=form.instance.file_format)

            if existing_download_list:
                # Check if any of the completed downloads are actually missing
                for down in existing_download_list:
                    down.set_missing_if_file_not_found()
                    down.save()
                fresh_existing_download_list = existing_download_list.filter(
                    status=Download.Status.COMPLETED)

                # Show the modal
                if fresh_existing_download_list:
                    context = {
                        'form': form,
                        'download': self.object,
                        'existing': fresh_existing_download_list,
                        'modal_title': 'Video with this Format Exists',
                        'modal_body': [
                            'This video has already been downloaded in this quality & format.',
                            'Please select to skip a fresh download and use the existing file.'
                        ],
                        'update': True
                    }
                    return render(self.request, "partials/download_format_form.html", context)

        worker_download.delay(self.object.pk)
        self.object.status = Download.Status.STARTED
        self.object.save()
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


class DownloadDetailView(LoginRequiredMixin, DetailView):
    model = Download
    template_name = "download_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        obj.set_missing_if_file_not_found()
        obj.save()
        context['download'] = obj
        return context


class DownloadArchiveView(LoginRequiredMixin, UpdateView):
    model = Download
    fields = []
    template_name = "download_confirm_delete.html"
    success_url = reverse_lazy('download:list')

    def form_valid(self, form):
        response = super().form_valid(form)
        obj = self.get_object()
        obj.archive_download()
        obj.save()
        return response


class DownloadCancelView(LoginRequiredMixin, UpdateView):
    model = Download
    fields = []
    template_name = "download_confirm_cancel.html"
    success_url = reverse_lazy('download:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        obj = self.get_object()
        app.control.revoke(obj.active_task_id,
                           terminate=True, signal='SIGUSR1')
        obj.cancel_download()
        obj.save()
        return response


class DownloadListView(LoginRequiredMixin, ListView):
    model = Download
    template_name = "download_list.html"
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q')
        filters = {
            'mine': Q(created_by=self.request.user),
            'q': Q(title__icontains=query) | Q(url__icontains=query)
        }
        selected_filters = [v for k,v in filters.items() if k in self.request.GET]
        if len(selected_filters) > 0:
            download_list = Download.objects.filter(*selected_filters)
        else:
            download_list = Download.objects.all()
        return download_list

    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        vals = {k: self.request.GET[k] for k in self.request.GET.keys() & {'q', 'mine'}}
        context.update(vals)
        return context


class DownloadProgressView(LoginRequiredMixin, View):
    def get(self, request, pk):
        download = Download.objects.get(pk=pk)
        if download.status == Download.Status.STARTED:
            task = AsyncResult(download.active_task_id)
            info = {'percent_str': '0.0%',
                    'percent': 0} if task.status is 'STARTED' else task.info
            context = {
                'task_status': task.status,
                'task_id': task.id,
                'task_info': info,
                'download': download,
                'trigger': 'load delay:600ms'
            }
        else:
            context = {'download': download, 'trigger': 'none'}

        return render(request, "partials/download_progress.html", context)


class RegisterView(SuccessMessageMixin, CreateView):
    template_name = 'registration/register.html'
    model = UserProfile
    form_class = UserRegisterForm
    success_message = "Your profile was initialized successfully. It will not be activated until the Admin approves your access."

    def form_valid(self, form):
        form.instance.is_approved = False
        form.send_email()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('login')
