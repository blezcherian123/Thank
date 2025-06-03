from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
import re
import spacy
from dateutil.parser import parse as parse_date
import random

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Load spaCy model for NLP
nlp = spacy.load("en_core_web_sm")

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

departments = ['General Medicine', 'Cardiology', 'Orthopedics', 'Pediatrics', 'Neurology']
hospital_info = {
    'timings': 'Open 24/7 for emergencies. Regular consultations: 8 AM - 8 PM, Monday to Saturday.',
    'departments': ', '.join(departments),
    'insurance': 'We accept major insurance plans including Aetna, Blue Cross, and Medicare. Please bring your insurance card.',
    'contact': 'Call us at (555) 123-4567 or email info@hospital.com.',
    'location': '123 Health St, Wellness City, HC 12345'
}

# Simulated available appointment slots
available_slots = {
    'Cardiology': ['2025-06-03 10:00', '2025-06-03 14:00', '2025-06-04 11:00'],
    'Orthopedics': ['2025-06-03 09:00', '2025-06-04 15:00'],
    'Pediatrics': ['2025-06-03 11:00', '2025-06-04 10:00'],
    'Neurology': ['2025-06-03 13:00', '2025-06-04 16:00'],
    'General Medicine': ['2025-06-03 08:00', '2025-06-03 12:00', '2025-06-04 09:00']
}

# Symptom-to-department mapping with weights
symptom_map = {
    'Cardiology': [
        (['heart', 'chest pain', 'palpitation', 'blood pressure', 'cardiac'], 0.9),
        (['shortness of breath', 'dizziness'], 0.7)
    ],
    'Orthopedics': [
        (['bone', 'joint', 'fracture', 'sprain', 'back pain'], 0.9),
        (['swelling', 'stiffness'], 0.7)
    ],
    'Pediatrics': [
        (['child', 'fever', 'cough', 'rash'], 0.9),
        (['infant', 'diarrhea'], 0.7)
    ],
    'Neurology': [
        (['headache', 'seizure', 'nerve', 'migraine', 'numbness'], 0.9),
        (['dizziness', 'memory loss'], 0.7)
    ],
    'General Medicine': [
        (['fatigue', 'nausea', 'pain'], 0.6)
    ]
}

def suggest_department(symptoms):
    doc = nlp(symptoms.lower())
    tokens = [token.text for token in doc]
    max_score = 0
    best_department = 'General Medicine'

    for dept, patterns in symptom_map.items():
        score = 0
        for keywords, weight in patterns:
            if any(keyword in symptoms for keyword in keywords):
                score += weight
        if score > max_score:
            max_score = score
            best_department = dept
    
    return best_department

def validate_appointment_time(time_input, department):
    try:
        parsed_time = parse_date(time_input, fuzzy=True, default=datetime.now())
        if parsed_time < datetime.now():
            return None, "The requested time is in the past. Please choose a future time."
        
        # Check available slots
        for slot in available_slots.get(department, []):
            slot_time = datetime.strptime(slot, '%Y-%m-%d %H:%M')
            if abs((parsed_time - slot_time).total_seconds()) <= 1800:  # 30-minute window
                return slot, f"Appointment confirmed for {slot} in {department}."
        return None, f"No available slots close to {time_input} in {department}. Try another time, e.g., 'tomorrow at 10 AM'."
    except ValueError:
        return None, "I couldn't understand the time. Please specify like 'tomorrow at 10 AM'."

@app.route('/process', methods=['POST'])
def process_input():
    data = request.json
    user_input = data['input'].lower().strip()
    state = data['state']
    user_data = data.get('userData', {'symptoms': '', 'name': '', 'time': '', 'department': ''})
    response = ''
    
    # Handle multiple intents
    intents = []
    if any(word in user_input for word in ['book', 'appointment', 'consultation']):
        intents.append('booking')
    if any(word in user_input for word in ['timing', 'hours']):
        intents.append('timings')
    if any(word in user_input for word in ['department', 'specialty']):
        intents.append('departments')
    if any(word in user_input for word in ['insurance']):
        intents.append('insurance')
    if any(word in user_input for word in ['contact', 'phone', 'email']):
        intents.append('contact')
    if any(word in user_input for word in ['location', 'address']):
        intents.append('location')

    if state == 'greeting':
        if len(intents) > 1:
            # Handle multiple intents
            responses = []
            for intent in intents:
                if intent == 'timings':
                    responses.append(hospital_info['timings'])
                elif intent == 'departments':
                    responses.append(f'Our departments include: {hospital_info["departments"]}.')
                elif intent == 'insurance':
                    responses.append(hospital_info['insurance'])
                elif intent == 'contact':
                    responses.append(hospital_info['contact'])
                elif intent == 'location':
                    responses.append(hospital_info['location'])
            response = ' '.join(responses) + ' Would you like to proceed with booking or have other questions?'
        elif 'booking' in intents:
            response = 'I can help you book a consultation. Please describe your symptoms or specify a department.'
            state = 'symptoms'
        elif 'timings' in intents:
            response = hospital_info['timings'] + ' Would you like to book a consultation or have other questions?'
        elif 'departments' in intents:
            response = f'Our departments include: {hospital_info["departments"]}. Would you like to book a consultation in one of these?'
        elif 'insurance' in intents:
            response = hospital_info['insurance'] + ' Do you have any other questions?'
        elif 'contact' in intents:
            response = hospital_info['contact'] + ' Anything else I can assist with?'
        elif 'location' in intents:
            response = hospital_info['location'] + ' Would you like directions or to book an appointment?'
        else:
            response = 'I’m here to assist with appointments or answer questions about our hospital. You can ask about timings, departments, insurance, or book a consultation.'
    
    elif state == 'symptoms':
        user_data['symptoms'] = user_input
        if any(dept.lower() in user_input for dept in departments):
            user_data['department'] = next(dept for dept in departments if dept.lower() in user_input)
            response = f'You’ve selected {user_data["department"]}. Please provide your full name.'
            state = 'name'
        else:
            user_data['department'] = suggest_department(user_input)
            response = f'Based on your symptoms ("{user_input}"), I recommend the {user_data["department"]} department. Is this okay, or would you like a different department?'
            state = 'confirm_department'
    
    elif state == 'confirm_department':
        if 'yes' in user_input or 'okay' in user_input or 'correct' in user_input:
            response = f'Great, we’ll proceed with {user_data["department"]}. Please provide your full name.'
            state = 'name'
        elif any(dept.lower() in user_input for dept in departments):
            user_data['department'] = next(dept for dept in departments if dept.lower() in user_input)
            response = f'You’ve selected {user_data["department"]}. Please provide your full name.'
            state = 'name'
        else:
            response = 'Would you like to proceed with the recommended department or choose another? You can say the department name or describe your symptoms again.'
    
    elif state == 'name':
        if re.match(r'^[a-zA-Z\s]+$', user_input):
            user_data['name'] = user_input.title()
            response = f'Thank you, {user_data["name"]}. Please provide your preferred appointment time, e.g., "tomorrow at 10 AM".'
            state = 'time'
        else:
            response = 'Please provide a valid full name (letters and spaces only).'
    
    elif state == 'time':
        user_data['time'] = user_input
        slot, message = validate_appointment_time(user_input, user_data['department'])
        if slot:
            user_data['confirmed_time'] = slot
            response = f'{message} Your appointment with {user_data["department"]} is set for {user_data["name"]}. Anything else I can help with?'
            state = 'confirm'
        else:
            response = message
            state = 'time'
    
    elif state == 'confirm':
        if any(word in user_input for word in ['no', 'thank you', 'done']):
            response = f'Thank you for contacting us, {user_data["name"]}. Have a great day!'
            state = 'greeting'
            user_data = {'symptoms': '', 'name': '', 'time': '', 'department': ''}
        else:
            response = 'Is there anything else I can assist you with, such as hospital information or another appointment?'
    
    return jsonify({'response': response, 'state': state, 'userData': user_data})

if __name__ == '__main__':
    app.run(debug=True)