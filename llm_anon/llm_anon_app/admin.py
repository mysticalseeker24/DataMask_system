from django.contrib import admin

from .models import *

admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(UseCase)
admin.site.register(Session)
admin.site.register(InitialInput)
admin.site.register(AnonymizedInput)
admin.site.register(AnonymizedOutput)
admin.site.register(EvalQuestion)
admin.site.register(EvalAnswer)