from abc import ABC, abstractmethod

class HandelQuestionStrategy(ABC):
    @abstractmethod
    def handel_question(self, question, r_type):
        pass

class HandelQuestionDetectLanguage(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionButton(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionList(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionSmartQuestion(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionCalendar(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionAPI(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionName(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionPhone(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionEmail(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionQuestion(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass 

class HandelQuestionNumber(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionDocument(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionImage(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionAudio(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionVideo(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionSticker(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass

class HandelQuestionContact(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    
class HandelQuestionLocation(HandelQuestionStrategy):
    def handel_question(self, question, r_type):
        pass
    

class MeassgeStrategyFactory:
    @abstractmethod
    def create_strategy(self, r_type):
        strategies = {
            "detect_language": HandelQuestionDetectLanguage(),
            "button": HandelQuestionButton(),
            "list": HandelQuestionList(),
            "smart_question": HandelQuestionSmartQuestion(),
            "calender": HandelQuestionCalendar(),
            "api": HandelQuestionAPI(),
            "name": HandelQuestionName(),
            "phone": HandelQuestionPhone(),
            "email": HandelQuestionEmail(),
            "question": HandelQuestionQuestion(),
            "number": HandelQuestionNumber(),
            "document": HandelQuestionDocument(),
            "image": HandelQuestionImage(),
            "audio": HandelQuestionAudio(),
            "video": HandelQuestionVideo(),
            "sticker": HandelQuestionSticker(),
            "contact": HandelQuestionContact(),
            "location": HandelQuestionLocation(),
        }

        return strategies.get(r_type)
    
class MessageSender:
    def __init__(self) -> None:
        self.strategy = None

    def set_strategy(self, r_type):
        self.strategy = MeassgeStrategyFactory.create_strategy(r_type)

    # def send(self, message, recipient):
    #     if self.strategy:
    #         self.strategy.send_message(message, recipient, question_type)
    #     else:
    #         print("No strategy set for this question type")