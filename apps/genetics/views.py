from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.genetics.forms import (
    EmbryoBatchForm,
    SemenBatchForm,
    StockAdjustmentForm,
    StorageTankForm,
)
from apps.genetics.models import EmbryoBatch, SemenBatch, StorageTank
from apps.genetics.services import GeneticsService


# Storage Tank Views
class StorageTankListView(LoginRequiredMixin, ListView):
    model = StorageTank
    template_name = "genetics/tank_list.html"
    context_object_name = "tanks"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_all_tanks()


class StorageTankDetailView(LoginRequiredMixin, DetailView):
    model = StorageTank
    template_name = "genetics/tank_detail.html"
    context_object_name = "tank"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["semen_batches"] = SemenBatch.objects.filter(tank=self.object).order_by(
            "canister"
        )
        context["embryo_batches"] = EmbryoBatch.objects.filter(
            tank=self.object
        ).order_by("canister")
        context["inventory_summary"] = GeneticsService.get_tank_inventory_summary(
            self.object
        )
        return context


class StorageTankCreateView(LoginRequiredMixin, CreateView):
    model = StorageTank
    form_class = StorageTankForm
    template_name = "genetics/tank_form.html"
    success_url = reverse_lazy("genetics:tank-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Storage Tank")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Storage tank created successfully."))
        return super().form_valid(form)


class StorageTankUpdateView(LoginRequiredMixin, UpdateView):
    model = StorageTank
    form_class = StorageTankForm
    template_name = "genetics/tank_form.html"
    success_url = reverse_lazy("genetics:tank-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Storage Tank")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Storage tank updated successfully."))
        return super().form_valid(form)


class StorageTankDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = StorageTank
    template_name = "genetics/tank_confirm_delete.html"
    success_url = reverse_lazy("genetics:tank-list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            GeneticsService.delete_tank(self.object)
            messages.success(request, _("Storage tank moved to trash."))
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.success_url)


class StorageTankTrashView(LoginRequiredMixin, ListView):
    model = StorageTank
    template_name = "genetics/tank_trash_list.html"
    context_object_name = "tanks"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_deleted_tanks()


class StorageTankRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            tank = StorageTank.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.restore_tank(tank)
            messages.success(request, _("Storage tank restored successfully."))
        except StorageTank.DoesNotExist:
            messages.error(request, _("Storage tank not found."))

        return HttpResponseRedirect(reverse_lazy("genetics:tank-list"))

    def get(self, request, pk):
        try:
            tank = StorageTank.all_objects.get(pk=pk, is_deleted=True)
            return render(request, "genetics/tank_confirm_restore.html", {"tank": tank})
        except StorageTank.DoesNotExist:
            messages.error(request, _("Storage tank not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:tank-list"))


class StorageTankPermanentDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, View
):
    def post(self, request, pk):
        try:
            tank = StorageTank.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.hard_delete_tank(tank)
            messages.success(request, _("Storage tank permanently deleted."))
        except StorageTank.DoesNotExist:
            messages.error(request, _("Storage tank not found."))
        except (ValidationError, ProtectedError) as e:
            tank = StorageTank.all_objects.get(pk=pk)
            self.object = tank
            return self.handle_delete_error(
                request,
                e,
                template_name="genetics/tank_confirm_permanent_delete.html",
                context_object_name="tank",
            )

        return HttpResponseRedirect(reverse_lazy("genetics:tank-trash"))

    def get(self, request, pk):
        try:
            tank = StorageTank.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request,
                "genetics/tank_confirm_permanent_delete.html",
                {"tank": tank},
            )
        except StorageTank.DoesNotExist:
            messages.error(request, _("Storage tank not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:tank-trash"))


# Semen Batch Views
class SemenBatchListView(LoginRequiredMixin, ListView):
    model = SemenBatch
    template_name = "genetics/semen_list.html"
    context_object_name = "semen_batches"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_all_semen_batches()


class SemenBatchDetailView(LoginRequiredMixin, DetailView):
    model = SemenBatch
    template_name = "genetics/semen_detail.html"
    context_object_name = "batch"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_form"] = StockAdjustmentForm(batch=self.object)
        return context


class SemenBatchCreateView(LoginRequiredMixin, CreateView):
    model = SemenBatch
    form_class = SemenBatchForm
    template_name = "genetics/semen_form.html"
    success_url = reverse_lazy("genetics:semen-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Semen Batch")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Semen batch created successfully."))
        return super().form_valid(form)


class SemenBatchUpdateView(LoginRequiredMixin, UpdateView):
    model = SemenBatch
    form_class = SemenBatchForm
    template_name = "genetics/semen_form.html"
    success_url = reverse_lazy("genetics:semen-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Semen Batch")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Semen batch updated successfully."))
        return super().form_valid(form)


class SemenBatchDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = SemenBatch
    template_name = "genetics/semen_confirm_delete.html"
    success_url = reverse_lazy("genetics:semen-list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            GeneticsService.delete_semen_batch(self.object)
            messages.success(request, _("Semen batch moved to trash."))
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.success_url)


class SemenBatchTrashView(LoginRequiredMixin, ListView):
    model = SemenBatch
    template_name = "genetics/semen_trash_list.html"
    context_object_name = "semen_batches"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_deleted_semen_batches()


class SemenBatchRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            batch = SemenBatch.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.restore_semen_batch(batch)
            messages.success(request, _("Semen batch restored successfully."))
        except SemenBatch.DoesNotExist:
            messages.error(request, _("Semen batch not found."))

        return HttpResponseRedirect(reverse_lazy("genetics:semen-list"))

    def get(self, request, pk):
        try:
            batch = SemenBatch.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request, "genetics/semen_confirm_restore.html", {"batch": batch}
            )
        except SemenBatch.DoesNotExist:
            messages.error(request, _("Semen batch not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:semen-list"))


class SemenBatchPermanentDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, View
):
    def post(self, request, pk):
        try:
            batch = SemenBatch.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.hard_delete_semen_batch(batch)
            messages.success(request, _("Semen batch permanently deleted."))
        except SemenBatch.DoesNotExist:
            messages.error(request, _("Semen batch not found."))
        except (ValidationError, ProtectedError) as e:
            batch = SemenBatch.all_objects.get(pk=pk)
            self.object = batch
            return self.handle_delete_error(
                request,
                e,
                template_name="genetics/semen_confirm_permanent_delete.html",
                context_object_name="batch",
            )

        return HttpResponseRedirect(reverse_lazy("genetics:semen-trash"))

    def get(self, request, pk):
        try:
            batch = SemenBatch.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request,
                "genetics/semen_confirm_permanent_delete.html",
                {"batch": batch},
            )
        except SemenBatch.DoesNotExist:
            messages.error(request, _("Semen batch not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:semen-trash"))


# Embryo Batch Views
class EmbryoBatchListView(LoginRequiredMixin, ListView):
    model = EmbryoBatch
    template_name = "genetics/embryo_list.html"
    context_object_name = "embryo_batches"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_all_embryo_batches()


class EmbryoBatchDetailView(LoginRequiredMixin, DetailView):
    model = EmbryoBatch
    template_name = "genetics/embryo_detail.html"
    context_object_name = "batch"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_form"] = StockAdjustmentForm(batch=self.object)
        return context


class EmbryoBatchCreateView(LoginRequiredMixin, CreateView):
    model = EmbryoBatch
    form_class = EmbryoBatchForm
    template_name = "genetics/embryo_form.html"
    success_url = reverse_lazy("genetics:embryo-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Embryo Batch")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Embryo batch created successfully."))
        return super().form_valid(form)


class EmbryoBatchUpdateView(LoginRequiredMixin, UpdateView):
    model = EmbryoBatch
    form_class = EmbryoBatchForm
    template_name = "genetics/embryo_form.html"
    success_url = reverse_lazy("genetics:embryo-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Embryo Batch")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Embryo batch updated successfully."))
        return super().form_valid(form)


class EmbryoBatchDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = EmbryoBatch
    template_name = "genetics/embryo_confirm_delete.html"
    success_url = reverse_lazy("genetics:embryo-list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            GeneticsService.delete_embryo_batch(self.object)
            messages.success(request, _("Embryo batch moved to trash."))
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.success_url)


class EmbryoBatchTrashView(LoginRequiredMixin, ListView):
    model = EmbryoBatch
    template_name = "genetics/embryo_trash_list.html"
    context_object_name = "embryo_batches"
    paginate_by = 20

    def get_queryset(self):
        return GeneticsService.get_deleted_embryo_batches()


class EmbryoBatchRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            batch = EmbryoBatch.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.restore_embryo_batch(batch)
            messages.success(request, _("Embryo batch restored successfully."))
        except EmbryoBatch.DoesNotExist:
            messages.error(request, _("Embryo batch not found."))

        return HttpResponseRedirect(reverse_lazy("genetics:embryo-list"))

    def get(self, request, pk):
        try:
            batch = EmbryoBatch.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request, "genetics/embryo_confirm_restore.html", {"batch": batch}
            )
        except EmbryoBatch.DoesNotExist:
            messages.error(request, _("Embryo batch not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:embryo-list"))


class EmbryoBatchPermanentDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, View
):
    def post(self, request, pk):
        try:
            batch = EmbryoBatch.all_objects.get(pk=pk, is_deleted=True)
            GeneticsService.hard_delete_embryo_batch(batch)
            messages.success(request, _("Embryo batch permanently deleted."))
        except EmbryoBatch.DoesNotExist:
            messages.error(request, _("Embryo batch not found."))
        except (ValidationError, ProtectedError) as e:
            batch = EmbryoBatch.all_objects.get(pk=pk)
            self.object = batch
            return self.handle_delete_error(
                request,
                e,
                template_name="genetics/embryo_confirm_permanent_delete.html",
                context_object_name="batch",
            )

        return HttpResponseRedirect(reverse_lazy("genetics:embryo-trash"))

    def get(self, request, pk):
        try:
            batch = EmbryoBatch.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request,
                "genetics/embryo_confirm_permanent_delete.html",
                {"batch": batch},
            )
        except EmbryoBatch.DoesNotExist:
            messages.error(request, _("Embryo batch not found."))
            return HttpResponseRedirect(reverse_lazy("genetics:embryo-trash"))


# Stock Adjustment Views
class SemenBatchStockAdjustmentView(LoginRequiredMixin, View):
    """View for adjusting semen batch stock manually."""

    def get(self, request, pk):
        batch = SemenBatch.objects.get(pk=pk)
        form = StockAdjustmentForm(batch=batch)
        return render(
            request,
            "genetics/stock_adjustment.html",
            {"form": form, "batch": batch, "batch_type": "Semen"},
        )

    def post(self, request, pk):
        batch = SemenBatch.objects.get(pk=pk)
        form = StockAdjustmentForm(request.POST, batch=batch)

        if form.is_valid():
            form.apply_adjustment()
            messages.success(
                request,
                _(
                    f"Stock adjusted successfully. New quantity: {batch.current_quantity}"
                ),
            )
            return HttpResponseRedirect(
                reverse_lazy("genetics:semen-detail", args=[batch.pk])
            )

        return render(
            request,
            "genetics/stock_adjustment.html",
            {"form": form, "batch": batch, "batch_type": "Semen"},
        )


class EmbryoBatchStockAdjustmentView(LoginRequiredMixin, View):
    """View for adjusting embryo batch stock manually."""

    def get(self, request, pk):

        batch = EmbryoBatch.objects.get(pk=pk)
        form = StockAdjustmentForm(batch=batch)
        return render(
            request,
            "genetics/stock_adjustment.html",
            {"form": form, "batch": batch, "batch_type": "Embryo"},
        )

    def post(self, request, pk):

        batch = EmbryoBatch.objects.get(pk=pk)
        form = StockAdjustmentForm(request.POST, batch=batch)

        if form.is_valid():
            form.apply_adjustment()
            messages.success(
                request,
                _(
                    f"Stock adjusted successfully. New quantity: {batch.current_quantity}"
                ),
            )
            return HttpResponseRedirect(
                reverse_lazy("genetics:embryo-detail", args=[batch.pk])
            )

        return render(
            request,
            "genetics/stock_adjustment.html",
            {"form": form, "batch": batch, "batch_type": "Embryo"},
        )
