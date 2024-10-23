from django.urls import path

from . import views

app_name = "llm_anon_app"
urlpatterns = [
    # path("", views.IndexView.as_view(), name="index"),
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    path("<int:question_id>/vote/", views.vote, name="vote"),

    # NER urls
    path("", views.ner, name="home"),
    path("ner/", views.ner, name="ner"),
    path("ner/<int:session_id>/", views.ner, name="ner"),
    path("ner_dict_update/", views.ner_dict_update, name="ner_dict_update"),

    # Masking urls
    path("masking/<int:session_id>/", views.masking, name="masking"),
    path("create_choices/", views.create_choices, name="create_choices"),
    path("perform_masking/", views.perform_masking, name="perform_masking"),
    path("send_to_llm/", views.send_to_llm, name="send_to_llm"),

    # Evaluation urls
    path("evaluation/<int:session_id>/", views.evaluation, name="evaluation"),
    path("insert_evaluation_answer/", views.insert_evaluation_answer, name="insert_evaluation_answer"),
]