from django.db import models
from django.utils import timezone

import datetime

class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")
    
    def __str__(self):
        return self.question_text
    
    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text
    
class UseCase(models.Model): 
    use_case = models.CharField(max_length=200)
    
    def __str__(self):
        return self.use_case
    
class Session(models.Model):
    session_id = models.CharField(max_length=200)
    pub_date = models.DateTimeField("time started")
    use_case = models.ForeignKey(UseCase, on_delete=models.DO_NOTHING, null=True)
    
    def __str__(self):
        return self.session_id

class InitialInput(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    input_text = models.TextField()
    pub_date = models.DateTimeField("time submitted")
    ner_dict = models.TextField()
    
    def __str__(self):
        return self.input_text

class AnonymizedInput(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    initial_input = models.ForeignKey(InitialInput, on_delete=models.CASCADE)
    pub_date = models.DateTimeField("time submitted")
    choice_dict = models.TextField()
    anon_input_text = models.TextField()
    
    def __str__(self):
        return self.anon_input_text

class AnonymizedOutput(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    anon_input = models.ForeignKey(AnonymizedInput, on_delete=models.CASCADE)
    pub_date = models.DateTimeField("time submitted")
    llm_output_text = models.TextField()
    unmasked_output_text = models.TextField()

    def __str__(self):
        return self.llm_output_text

class EvalQuestion(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")
    use_case = models.ForeignKey(UseCase, on_delete=models.DO_NOTHING, null=True)
    
    def __str__(self):
        return self.question_text

class EvalAnswer(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True)
    question = models.ForeignKey(EvalQuestion, on_delete=models.CASCADE)
    answer_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    def __str__(self):
        return self.answer_text
    
class LLMPrompt(models.Model):
    prompt_text = models.TextField()
    use_case = models.ForeignKey(UseCase, on_delete=models.DO_NOTHING, null=True)
    
    def __str__(self):
        return self.prompt_text

