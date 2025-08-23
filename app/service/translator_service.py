from deep_translator import GoogleTranslator

class TranslationService:
    def __init__(self):
        self.translator = GoogleTranslator()

    def preprocessing(self, text):
        return text.lower()

    def translate(self, text):
        text = self.preprocessing(text)
        return self.translator.translate(text)
