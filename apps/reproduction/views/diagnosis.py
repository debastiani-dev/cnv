from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView

from apps.base.views.list_mixins import StandardizedListMixin
from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from apps.reproduction.services.reproduction_service import ReproductionService

DIAGNOSIS_LIST_URL = "reproduction:diagnosis_list"
PREGNANCY_CHECK_NOT_FOUND_MSG = _("Pregnancy Check not found.")


class DiagnosisListView(StandardizedListMixin, ListView):
    model = PregnancyCheck
    template_name = "reproduction/pregnancy_check_list.html"
    context_object_name = "checks"
    paginate_by = 20

    def get_queryset(self):
        queryset = PregnancyCheck.objects.select_related(
            "breeding_event__dam"
        ).order_by("-date")

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(breeding_event__dam__tag__icontains=search_query)

        result = self.request.GET.get("result")
        if result:
            queryset = queryset.filter(result=result)

        queryset = self.filter_by_date(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # search_query and dates handled by mixin

        context["selected_result"] = self.request.GET.get("result", "")

        context["result_choices"] = PregnancyCheck.RESULT_CHOICES

        return context


class DiagnosisCreateView(CreateView):
    model = PregnancyCheck
    fields = ["breeding_event", "date", "result", "fetus_days"]
    template_name = "reproduction/pregnancy_check_form.html"
    success_url = reverse_lazy(DIAGNOSIS_LIST_URL)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limit choices to cows that are BRED (and thus waiting for diagnosis)
        # Or maybe allow re-checking pregnant ones? For MVP, BRED is safest default.
        form.fields["breeding_event"].queryset = (
            BreedingEvent.objects.filter(
                dam__reproduction_status=Cattle.REP_STATUS_BRED
            )
            .select_related("dam")
            .order_by("-date")
        )
        # Improved label for dropdown in form/model would be nice (__str__ handles it)
        return form

    def form_valid(self, form):
        try:
            ReproductionService.record_diagnosis(
                breeding_event=form.cleaned_data["breeding_event"],
                date=form.cleaned_data["date"],
                result=form.cleaned_data["result"],
                fetus_days=form.cleaned_data["fetus_days"],
            )
            messages.success(self.request, _("Diagnosis recorded successfully."))
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class DiagnosisDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            check = PregnancyCheck.objects.get(pk=pk)
            check.delete()
            messages.success(request, _("Pregnancy Check deleted."))
        except ProtectedError as e:
            messages.error(request, str(e))
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)

        return redirect(DIAGNOSIS_LIST_URL)

    def get(self, request, pk):
        try:
            check = PregnancyCheck.objects.get(pk=pk)
            return render(
                request,
                "reproduction/pregnancy_check_confirm_delete.html",
                {"object": check},
            )
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)
            return redirect(DIAGNOSIS_LIST_URL)


class DiagnosisTrashListView(LoginRequiredMixin, ListView):
    model = PregnancyCheck
    template_name = "reproduction/pregnancy_check_trash_list.html"
    context_object_name = "checks"

    def get_queryset(self):
        return ReproductionService.get_deleted_pregnancy_checks()


class DiagnosisRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            ReproductionService.restore_pregnancy_check(pk)
            messages.success(request, _("Pregnancy Check restored successfully."))
        except ValueError as e:
            messages.error(request, str(e))
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)

        return redirect(DIAGNOSIS_LIST_URL)

    def get(self, request, pk):
        try:
            event = PregnancyCheck.all_objects.get(pk=pk)
            return render(
                request,
                "reproduction/pregnancy_check_confirm_restore.html",
                {"event": event},
            )
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)
            return redirect(DIAGNOSIS_LIST_URL)


class DiagnosisPermanentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            ReproductionService.hard_delete_pregnancy_check(pk)
            messages.success(request, _("Pregnancy Check permanently deleted."))
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)

        return redirect("reproduction:diagnosis_trash")

    def get(self, request, pk):
        try:
            event = PregnancyCheck.all_objects.get(pk=pk)
            return render(
                request,
                "reproduction/pregnancy_check_confirm_permanent_delete.html",
                {"event": event},
            )
        except PregnancyCheck.DoesNotExist:
            messages.error(request, PREGNANCY_CHECK_NOT_FOUND_MSG)
            return redirect("reproduction:diagnosis_trash")
