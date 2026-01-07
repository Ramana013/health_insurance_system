from django.urls import path
from . import views
from .views import (
    DashboardView,
    FeedbackListView,
    SubmitFeedbackView,
    ViewFeedbackView,
    EditFeedbackView,
    get_feedback_comments
)

app_name = 'feedback_support'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('list/', FeedbackListView.as_view(), name='feedback_list'),
    path('submit/', SubmitFeedbackView.as_view(), name='submit_feedback'),
    path('view/<str:ticket_id>/', ViewFeedbackView.as_view(), name='view_feedback'),
    path('edit/<str:ticket_id>/', EditFeedbackView.as_view(), name='edit_feedback'),
    path('ajax/comments/<str:ticket_id>/', views.get_feedback_comments, name='get_comments'),

]