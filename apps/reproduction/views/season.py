from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.reproduction.forms import ReproductiveSeasonForm
from apps.reproduction.models import ReproductiveSeason


class SeasonListView(LoginRequiredMixin, ListView):
    model = ReproductiveSeason
    template_name = "reproduction/season_list.html"
    context_object_name = "seasons"
    ordering = ["-start_date"]


class SeasonCreateView(LoginRequiredMixin, CreateView):
    model = ReproductiveSeason
    form_class = ReproductiveSeasonForm
    template_name = "reproduction/season_form.html"
    success_url = reverse_lazy("reproduction:season_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Reproductive Season")
        return context


class SeasonUpdateView(LoginRequiredMixin, UpdateView):
    model = ReproductiveSeason
    form_class = ReproductiveSeasonForm
    template_name = "reproduction/season_form.html"
    success_url = reverse_lazy("reproduction:season_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Reproductive Season")
        return context


class SeasonDeleteView(LoginRequiredMixin, DeleteView):
    model = ReproductiveSeason
    template_name = "reproduction/season_confirm_delete.html"
    success_url = reverse_lazy("reproduction:season_list")
