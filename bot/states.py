# FSM States
from aiogram.fsm.state import StatesGroup, State

class States(StatesGroup):
    start = State()
    mode_selection = State()
    ration_selected = State()
    days_count_selection = State()
    calendar_selection = State()
    day_selected = State()
    meal_action_selection = State()
    swap_selection = State()
    base_swap_confirmation = State()
    add_on_quantity_input = State()
    cart_review = State()
    order_details_input = State()
    # Sequential contact info collection
    contact_first_name = State()
    contact_last_name = State()
    contact_phone = State()
    contact_address = State()
    contact_postcode = State()
    contact_entrance = State()
    contact_floor = State()
    contact_apartment = State()
    contact_comment = State()
    contact_confirm = State()
    # Payment
    payment_method_selection = State()
    cash_change_selection = State()
    cash_bill_input = State()
    
    # Калькулятор ккал
    calculator_gender = State()
    calculator_age = State()
    calculator_height = State()
    calculator_weight = State()
    calculator_activity = State()
    calculator_goal = State()
    calculator_confirm = State()
    
    # Выбор рациона после расчета
    calculator_ration_selection = State()
    
    # Консультация с менеджером
    manager_consultation = State()
    
    # Профиль - добавление доп рациона
    profile_additional_ration = State()
