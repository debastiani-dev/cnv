from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.reproduction.forms import ReproductiveSeasonForm
from apps.reproduction.models import ReproductiveSeason
from apps.reproduction.services.reproduction_service import ReproductionService


class SeasonListView(LoginRequiredMixin, ListView):
    model = ReproductiveSeason
    template_name = "reproduction/season_list.html"
    context_object_name = "seasons"
    context_object_name = "seasons"
    paginate_by = 20
    ordering = ["-start_date"]

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        start_date = self.request.GET.get("start_date")
        end_date = self.request.GET.get("end_date")

        # Overlap filter or simple start/end range?
        # Typically looking for seasons starting within range?
        # Or active during?
        # Let's do simple start_date range for now.
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["start_date"] = self.request.GET.get("start_date", "")
        context["end_date"] = self.request.GET.get("end_date", "")
        return context


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


class SeasonDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        season = ReproductiveSeason.objects.get(pk=pk)
        return render(
            request, "reproduction/season_confirm_delete.html", {"object": season}
        )

    def post(self, request, pk):
        season = ReproductiveSeason.objects.get(pk=pk)
        try:
            season.delete()
            messages.success(request, _("Reproductive Season deleted."))
            return redirect("reproduction:season_list")
        except ProtectedError as e:
            messages.error(
                request,
                _(
                    "Cannot delete this Reproductive Season because it is referenced by other objects."
                ),
            )
            return render(
                request,
                "reproduction/season_confirm_delete.html",
                {"object": season, "error": str(e)},
            )


class SeasonTrashListView(LoginRequiredMixin, ListView):
    template_name = "reproduction/season_trash_list.html"
    context_object_name = "seasons"

    def get_queryset(self):
        return ReproductionService.get_deleted_seasons()


class SeasonRestoreView(LoginRequiredMixin, View):
    def get(self, request, pk):
        season = ReproductiveSeason.all_objects.get(pk=pk)
        return render(
            request, "reproduction/season_confirm_restore.html", {"object": season}
        )

    def post(self, request, pk):
        ReproductionService.restore_season(pk)
        messages.success(request, _("Reproductive Season restored."))
        return redirect("reproduction:season_trash")


class SeasonPermanentDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        season = ReproductiveSeason.all_objects.get(pk=pk)
        return render(
            request,
            "reproduction/season_confirm_permanent_delete.html",
            {"object": season},
        )

    def post(self, request, pk):
        ReproductionService.hard_delete_season(pk)
        messages.success(request, _("Reproductive Season permanently deleted."))
        return redirect("reproduction:season_trash")
