# admin_panel/reports.py
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse, JsonResponse

from claims.models import Claim
from policies.models import Policy, PolicyPurchase
from providers.models import NetworkProvider


class ReportGenerator:
    """Base class for report generation"""

    @staticmethod
    def get_date_range(request):
        """Get date range from request or default to last 30 days"""
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if not start_date:
            start_date = (timezone.now() - timedelta(days=30)).date()
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        if not end_date:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        return start_date, end_date


class ClaimsReport(ReportGenerator):
    """Claims-related reports"""

    @staticmethod
    def get_claims_summary(start_date, end_date):
        """Get claims summary statistics"""
        claims = Claim.objects.filter(
            created_at__date__range=[start_date, end_date]
        )

        total_claims = claims.count()
        approved_claims = claims.filter(status='Approved').count()
        pending_claims = claims.filter(status='Pending').count()

        return {
            'total_claims': total_claims,
            'approved_claims': approved_claims,
            'pending_claims': pending_claims,
            'claims_queryset': claims
        }

    @staticmethod
    def get_monthly_claims_growth():
        """Calculate monthly claims growth"""
        last_month = timezone.now() - timedelta(days=30)

        current_month_claims = Claim.objects.filter(
            created_at__gte=last_month
        ).count()

        previous_month_claims = Claim.objects.filter(
            created_at__gte=last_month - timedelta(days=30),
            created_at__lt=last_month
        ).count()

        monthly_growth = round(
            ((current_month_claims - previous_month_claims) / previous_month_claims * 100)
            if previous_month_claims > 0 else 0,
            1
        )

        return monthly_growth


class PolicyReport(ReportGenerator):
    """Policy-related reports"""

    @staticmethod
    def get_policy_usage_stats(start_date, end_date):
        """Get policy usage statistics"""
        active_policies = PolicyPurchase.objects.filter(
            is_active=True,
            purchased_on__date__range=[start_date, end_date]
        ).count()

        total_policies = Policy.objects.count()
        policy_utilization = round((active_policies / total_policies * 100) if total_policies > 0 else 0, 1)

        return {
            'active_policies': active_policies,
            'policy_utilization': policy_utilization
        }


class ProviderReport(ReportGenerator):
    """Provider-related reports"""

    @staticmethod
    def get_provider_performance():
        """Get provider performance statistics"""
        total_providers = NetworkProvider.objects.count()

        avg_provider_rating = NetworkProvider.objects.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
        avg_provider_rating = round(avg_provider_rating, 1)

        top_providers = NetworkProvider.objects.annotate(
            total_claims=Count('claim')
        ).order_by('-total_claims')[:5]

        return {
            'total_providers': total_providers,
            'avg_provider_rating': avg_provider_rating,
            'top_providers': top_providers
        }


class TrendsReport(ReportGenerator):
    """Trends-related reports"""

    @staticmethod
    def get_chart_data(chart_type):
        """Get chart data for visualization"""
        months = []
        data = []

        for i in range(6, 0, -1):
            month_date = timezone.now() - timedelta(days=30 * i)
            month = month_date.strftime('%b')
            months.append(month)

            if chart_type == 'claims':
                count = Claim.objects.filter(
                    created_at__month=month_date.month,
                    created_at__year=month_date.year
                ).count()
            elif chart_type == 'policies':
                count = PolicyPurchase.objects.filter(
                    purchased_on__month=month_date.month,
                    purchased_on__year=month_date.year
                ).count()
            else:
                count = 0

            data.append(count)

        return {'labels': months, 'data': data}


class ReportExporter:
    """Handle report export functionality"""

    @staticmethod
    def export_to_pdf(data, title, data_type='queryset'):
        """Export data to PDF format"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Add title
        title_style = styles['Heading1']
        title_style.alignment = 1
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Paragraph("<br/><br/>", styles['Normal']))

        # Create table based on data type
        if data_type == 'trends':
            table_data = ReportExporter._format_trends_data(data)
        else:
            table_data = ReportExporter._format_queryset_data(data)

        # Create table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        doc.build(story)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title.lower().replace(" ", "_")}.pdf"'
        return response

    @staticmethod
    def export_to_csv(data, report_type, data_type='queryset'):
        """Export data to CSV format"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'

        writer = csv.writer(response)

        if data_type == 'trends':
            writer.writerow(['Month', 'Claims', 'Policies', 'Revenue'])
            for i in range(len(data['months'])):
                writer.writerow([
                    data['months'][i],
                    data['claims'][i],
                    data['policies'][i],
                    data['revenue'][i]
                ])
        else:
            table_data = ReportExporter._format_queryset_data(data, for_csv=True)
            for row in table_data:
                writer.writerow(row)

        return response

    @staticmethod
    def _format_trends_data(data):
        """Format trends data for table"""
        table_data = [['Month', 'Claims', 'Policies', 'Revenue']]
        for i in range(len(data['months'])):
            table_data.append([
                data['months'][i],
                data['claims'][i],
                data['policies'][i],
                f"${data['revenue'][i]:,}"
            ])
        return table_data

    @staticmethod
    def _format_queryset_data(data, for_csv=False):
        """Format queryset data for table"""
        if hasattr(data, 'model'):
            model_name = data.model.__name__

            if model_name == 'Claim':
                headers = ['Claim ID', 'User', 'Policy', 'Amount', 'Status', 'Date']
                table_data = [headers]
                for item in data:
                    row = [
                        item.claim_id,
                        item.user.get_full_name(),
                        item.policy.name,
                        f"${item.amount}" if not for_csv else item.amount,
                        item.status,
                        item.created_at.strftime('%Y-%m-%d')
                    ]
                    table_data.append(row)

            elif model_name == 'Policy':
                headers = ['Policy Name', 'Total Purchases', 'Active Purchases', 'Premium']
                table_data = [headers]
                for item in data:
                    row = [
                        item.name,
                        item.total_purchases,
                        item.active_purchases,
                        f"${item.premium}" if not for_csv else item.premium
                    ]
                    table_data.append(row)

            elif model_name == 'NetworkProvider':
                headers = ['Provider Name', 'Total Claims', 'Avg Claim Amount', 'Success Rate']
                table_data = [headers]
                for item in data:
                    row = [
                        item.name,
                        item.total_claims,
                        f"${item.avg_claim_amount or 0:.2f}" if not for_csv else (item.avg_claim_amount or 0),
                        f"{item.success_rate or 0:.1f}%" if not for_csv else (item.success_rate or 0)
                    ]
                    table_data.append(row)
            else:
                table_data = [['No data available']]
        else:
            table_data = [['Invalid data format']]

        return table_data