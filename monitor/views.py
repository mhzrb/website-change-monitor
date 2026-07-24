from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404

from .forms import SignUpForm, WatchedSiteForm
from .models import WatchedSite, ChangeEvent
from .tasks import check_site


class CustomLoginView(LoginView):
    template_name = "monitor/login.html"


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("site_list")
    else:
        form = SignUpForm()
    return render(request, "monitor/signup.html", {"form": form})


@login_required
def site_list(request):
    sites = WatchedSite.objects.filter(user=request.user)
    return render(request, "monitor/site_list.html", {"sites": sites})


@login_required
def site_create(request):
    if request.method == "POST":
        form = WatchedSiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.user = request.user
            site.save()
            return redirect("site_list")
    else:
        form = WatchedSiteForm()
    return render(request, "monitor/site_form.html", {"form": form, "title": "Watch a new site"})


@login_required
def site_delete(request, pk):
    site = get_object_or_404(WatchedSite, pk=pk, user=request.user)
    if request.method == "POST":
        site.delete()
        return redirect("site_list")
    return render(request, "monitor/site_confirm_delete.html", {"site": site})


@login_required
def site_check_now(request, pk):
    """Manually trigger a check right away, instead of waiting for the schedule."""
    site = get_object_or_404(WatchedSite, pk=pk, user=request.user)
    try:
        check_site.delay(site.id)
    except Exception:
        # Redis/Celery worker not running — fall back to running it inline
        # so the button still works during local testing without extra setup.
        check_site(site.id)
    return redirect("site_list")


@login_required
def change_history(request, pk):
    site = get_object_or_404(WatchedSite, pk=pk, user=request.user)
    changes = ChangeEvent.objects.filter(site=site)
    return render(request, "monitor/change_history.html", {"site": site, "changes": changes})
