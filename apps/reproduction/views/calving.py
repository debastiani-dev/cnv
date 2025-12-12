from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView

from apps.base.views.list_mixins import StandardizedListMixin
from apps.reproduction.forms import CalvingForm
from apps.reproduction.models import Calving
from apps.reproduction.services.reproduction_service import ReproductionService


class CalvingListView(LoginRequiredMixin, StandardizedListMixin, ListView):
    model = Calving
    template_name = "reproduction/calving_list.html"
    context_object_name = "calvings"
    paginate_by = 20

    def get_queryset(self):
        queryset = Calving.objects.select_related("dam", "calf").order_by("-date")

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(dam__tag__icontains=search_query)
                | Q(calf__tag__icontains=search_query)
            )

        ease = self.request.GET.get("ease")
        if ease:
            queryset = queryset.filter(ease_of_birth=ease)

        queryset = self.filter_by_date(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # search_query and dates handled by mixin

        context["selected_ease"] = self.request.GET.get("ease", "")

        context["ease_choices"] = Calving.EASE_CHOICES

        return context


class CalvingCreateView(CreateView):
    model = Calving
    form_class = CalvingForm
    template_name = "reproduction/calving_form.html"
    success_url = reverse_lazy("reproduction:calving_list")

    def form_valid(self, form):
        try:
            calf_data = {
                "tag": form.cleaned_data["calf_tag"],
                "name": form.cleaned_data["calf_name"],
                "sex": form.cleaned_data["calf_sex"],
                "weight_kg": form.cleaned_data["calf_weight"],
            }

            ReproductionService.register_birth(
                dam=form.cleaned_data["dam"],
                date=form.cleaned_data["date"],
                breeding_event=form.cleaned_data["breeding_event"],
                calf_data=calf_data,
                ease_of_birth=form.cleaned_data["ease_of_birth"],
                notes=form.cleaned_data["notes"],
            )
            messages.success(
                self.request, _("Calving recorded and new Calf registered.")
            )
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class CalvingDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        calving = Calving.objects.get(pk=pk)
        return render(
            request, "reproduction/calving_confirm_delete.html", {"object": calving}
        )

    def post(self, request, pk):
        calving = Calving.objects.get(pk=pk)
        try:
            calving.delete()
            messages.success(request, _("Calving record deleted."))
            return redirect("reproduction:calving_list")
        except ProtectedError as e:
            messages.error(
                request,
                _(
                    "Cannot delete this calving record because it is referenced by other objects."
                ),
            )
            return render(
                request,
                "reproduction/calving_confirm_delete.html",
                {"object": calving, "error": str(e)},
            )


class CalvingTrashListView(LoginRequiredMixin, ListView):
    template_name = "reproduction/calving_trash_list.html"
    context_object_name = "records"

    def get_queryset(self):
        return ReproductionService.get_deleted_calving_records()


class CalvingRestoreView(LoginRequiredMixin, View):
    def get(self, request, pk):
        record = Calving.all_objects.get(pk=pk)
        return render(
            request, "reproduction/calving_confirm_restore.html", {"object": record}
        )

    def post(self, request, pk):
        ReproductionService.restore_calving_record(pk)
        messages.success(request, _("Calving record restored."))
        return redirect("reproduction:calving_trash")


class CalvingPermanentDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        record = Calving.all_objects.get(pk=pk)
        return render(
            request,
            "reproduction/calving_confirm_permanent_delete.html",
            {"object": record},
        )

    def post(self, request, pk):
        ReproductionService.hard_delete_calving_record(pk)
        messages.success(request, _("Calving record permanently deleted."))
        return redirect("reproduction:calving_trash")
