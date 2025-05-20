from mimesis import Person
from mimesis.enums import Gender
from mimesis import Locale
from mimesis import Text
t = Text(locale=Locale.ZH)
print(t.text(10))
print(t.title())
zh = Person(Locale.ZH)
en = Person('en')

print(en.full_name())
print(zh.full_name(gender=Gender.MALE))

print(zh.email(domains=["danwen.com", "163.com", "qq.com"]))