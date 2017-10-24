from datetime import date
from decimal import Decimal

from dateutil import relativedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth

from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET

from finance.forms import InterestForm
from finance.models import Interest, Contribution, Loan, Investment
from home.forms import DetailsForm
from home.models import ClubDetails
from users.models import User


@require_GET
def no_script(request):
    return render(request, 'error/no_script.html')


def custom_page_not_found(request):
    return render(request, 'error/404.html', status=404)


def custom_server_error(request):
    return render(request, 'error/500.html', status=500)


def custom_permission_denied(request):
    return render(request, 'error/403.html', status=403)


def custom_bad_request(request):
    return render(request, 'error/400.html', status=400)


def index(request):

    if not request.user.user_type == "admin":
        return redirect('profile_page')

    error = {}
    message = None

    today = date.today()
    start_date = today
    monthly_rate = 0
    total_membership = 0
    loan_rate = 0
    months_in_operation = 0

    expected_total_contributions = 0
    expected_total_cash_at_hand = 0
    banked_cash_at_hand = 0
    un_banked_cash_at_hand = 0

    form = DetailsForm()
    i_form = InterestForm()

    if request.POST:
        interest = request.POST.get('hidden_interest', False)
        details = request.POST.get('hidden_details', False)

        if interest:
            save = save_interest(request, interest)
            if save['status']:
                message = 'Interest rate updated.'
            else:
                i_form = save['form']
                error['error'] = 'Failed to complete transaction.'
                error['form'] = 'interest'

        elif details:
            save = save_details(request, details)
            if save['status']:
                message = 'Update has been successful.'
            else:
                form = save['form']
                error['error'] = 'Failed to complete transaction.'
                error['form'] = 'details'

    dt = ClubDetails.objects.all()
    if dt and dt.count() > 0:
        dt = dt[0]
        start_date = dt.start_date
        monthly_rate = dt.monthly_contribution
        months_passed = relativedelta.relativedelta(timezone.now(), start_date)
        if months_passed.years:
            months_in_operation = months_passed.years * 12
        if months_passed.months:
            months_in_operation += months_passed.months

        form = DetailsForm(instance=dt)

    ir = Interest.objects.all()
    if ir and ir.count() > 0:
        ir = ir[0]
        loan_rate = ir.interest
        i_form = InterestForm(instance=ir)

    u = User.objects.all()
    if u:
        total_membership = u.count()
        for user in u:
            expected_total_contributions += calculate_user_expected_amount(user, monthly_rate, today)

    return render(request, 'home/dashboard.html',
                  {
                      'title': "Admin Dashboard",
                      'no_search': True,
                      'form': form,
                      'i_form': i_form,
                      'loan_rate': loan_rate,
                      'today': today,
                      'start_date': start_date,
                      'months_in_operation': months_in_operation,
                      'total_membership': total_membership,
                      'monthly_rate': monthly_rate,
                      'expected_total_contributions': expected_total_contributions,
                      'expected_total_cash_at_hand': expected_total_cash_at_hand,
                      'banked_cash_at_hand': banked_cash_at_hand,
                      'unbanked_cash_at_hand': un_banked_cash_at_hand,
                      'error': error,
                      'message': message,
                      'all_contributions': all_contributions(monthly_rate, today),
                      'all_loans': all_loans(),
                      'all_investments': all_investments(),
                  })


def save_interest(request, hid=None):
    try:
        hid = int(hid)
    except TypeError:
        hid = None
    except ValueError:
        hid = None

    save = {}

    if hid is not None and hid == 1:
        try:
            ob = Interest.objects.all()
            interest_form = InterestForm(request.POST)
            if ob:
                ob = ob[0]
                interest_form = InterestForm(request.POST, instance=ob)
            if interest_form.is_valid():
                interest_form.save()
                save['form'] = ''
                save['status'] = True
            else:
                save['form'] = interest_form
                save['status'] = False

        except Interest.DoesNotExist:
            interest_form = InterestForm(request.POST)
            if interest_form.is_valid():
                interest_form.save()
                save['form'] = ''
                save['status'] = True
            else:
                save['form'] = interest_form
                save['status'] = False
    return save


def save_details(request, hid=None):
    try:
        hid = int(hid)
    except TypeError:
        hid = None
    except ValueError:
        hid = None

    save = {}

    if hid is not None and hid == 1:
        try:
            ob = ClubDetails.objects.all()
            detail_form = DetailsForm(request.POST)
            if ob:
                ob = ob[0]
                detail_form = DetailsForm(request.POST, instance=ob)
            if detail_form.is_valid():
                detail_form.save()
                save['form'] = ''
                save['status'] = True
            else:
                save['form'] = detail_form
                save['status'] = False

        except ClubDetails.DoesNotExist:
            detail_form = DetailsForm(request.POST)
            if detail_form.is_valid():
                detail_form.save()
                save['form'] = ''
                save['status'] = True
            else:
                save['form'] = detail_form
                save['status'] = False
    return save


def all_investments():
    investments = Investment.objects.all()
    return investments


def all_contributions(monthly=0, today=None):
    if not today:
        today = date.today()

    c = Contribution.objects.all()
    users = User.objects.all()

    data = []
    if users:
        total = 0
        outstanding = 0
        for us in users:
            d = c.filter(user=us).aggregate(totals=Sum('total'))
            if not d:
                data.append({
                    'name': us,
                    'status': us.user_status,
                    'paid': 0,
                    'balance': 0
                })
            else:

                this_month = Contribution.objects.filter(user=us, contribution_date__month=today.month)\
                    .aggregate(Sum('total'))
                if not this_month['total__sum']:
                    this_month['total__sum'] = 0

                balance = Decimal(monthly - this_month['total__sum'])
                if balance.as_tuple().sign == 1:
                    balance = 0

                total_b = Contribution.objects.filter(user=us).annotate(month=TruncMonth('contribution_date')) \
                    .values('month').annotate(paid=Sum('total')).order_by('-month')

                total_balance = 0
                for t in total_b:
                    p = t['paid']
                    y = t['month'].year
                    m = t['month'].month

                    if y == today.year and m == today.month:
                        continue

                    if total_balance.as_tuple().sign == 1:
                        total_balance += 0
                    else:
                        total_balance += Decimal(monthly - p)

                else:
                    total_balance += balance

                paid = d['totals']
                if not paid:
                    paid = 0
                data.append({
                    'name': us,
                    'status': us.user_status,
                    'paid': paid,
                    'balance': total_balance
                })
                total += paid
                outstanding += total_balance

        data.append({
            'total_paid': total,
            'total_balance': outstanding
        })

    return data


def calculate_user_expected_amount(user, monthly, today):

    months_passed = relativedelta.relativedelta(timezone.now(), user.date_joined)

    passed = 0
    if months_passed.years and months_passed.months:
        passed = (months_passed.years * 12) + months_passed.months
    elif months_passed.years and not months_passed.months:
        passed = (months_passed.years * 12)
    elif months_passed.months and not months_passed.years:
        passed = months_passed.months
    elif not months_passed.months and not months_passed.years:
        if months_passed.days:
            num = Contribution.objects.filter(user=user).annotate(month=TruncMonth('contribution_date')) \
                .values('month').annotate(num=Count('month')).order_by('month')
            if num:
                passed = num.count()
                if num[passed - 1]['month'].year == timezone.now().year and num[passed - 1]['month'].month < \
                        timezone.now().month:
                    passed += 1
            else:
                passed += 1
        elif months_passed.hours or months_passed.minutes and not months_passed.days:
            passed += 1

    expected = monthly * passed

    return expected


def all_loans():
    return Loan.objects.all().order_by('user__first_name', 'user__last_name')