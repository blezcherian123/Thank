const callButton = document.getElementById('callButton');
const endCallButton = document.getElementById('endCallButton');
const callStatus = document.getElementById('callStatus');
const statusText = document.getElementById('statusText');
const transcript = document.getElementById('transcript');
const appointmentSummary = document.getElementById('appointmentSummary');

let recognition;
let isCallActive = false;
let conversationState = 'greeting';
let userData = { symptoms: '', name: '', time: '', department: '' };
let conversationHistory = [];

// Initialize Web Speech API
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
        const userText = event.results[event.results.length - 1][0].transcript.trim();
        addToTranscript('You', userText);
        conversationHistory.push({ speaker: 'You', text: userText });
        processUserInput(userText);
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        let errorMessage = 'Sorry, I couldn’t hear you clearly. Please try speaking again.';
        if (event.error === 'no-speech') {
            errorMessage = 'No speech detected. Please try again.';
        } else if (event.error === 'network') {
            errorMessage = 'Network issue. Please check your connection.';
        }
        updateStatus(errorMessage);
        speak(errorMessage);
    };

    recognition.onend = () => {
        if (isCallActive) {
            recognition.start(); // Restart recognition if call is still active
        }
    };
}

function addToTranscript(speaker, text) {
    const div = document.createElement('div');
    div.className = speaker === 'You' ? 'transcript-user' : 'transcript-ai';
    const timestamp = new Date().toLocaleTimeString();
    div.textContent = `[${timestamp}] ${speaker}: ${text}`;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
}

function updateStatus(text) {
    statusText.textContent = text;
    callStatus.classList.remove('d-none');
}

function updateAppointmentSummary() {
    if (userData.name && userData.department && userData.time) {
        appointmentSummary.innerHTML = `
            <h5>Appointment Summary</h5>
            <p><strong>Name:</strong> ${userData.name}</p>
            <p><strong>Department:</strong> ${userData.department}</p>
            <p><strong>Time:</strong> ${userData.time}</p>
        `;
        appointmentSummary.classList.remove('d-none');
    } else {
        appointmentSummary.classList.add('d-none');
    }
}

function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
    addToTranscript('AI Receptionist', text);
    conversationHistory.push({ speaker: 'AI Receptionist', text });
}

async function processUserInput(input) {
    try {
        const response = await fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input, state: conversationState, userData })
        });
        if (!response.ok) {
            throw new Error('Server error');
        }
        const data = await response.json();
        conversationState = data.state;
        userData = data.userData;
        speak(data.response);
        updateAppointmentSummary();
    } catch (error) {
        console.error('Error processing input:', error);
        const errorMessage = 'Sorry, there was an issue processing your request. Please try again.';
        speak(errorMessage);
        updateStatus(errorMessage);
    }
}

callButton.addEventListener('click', () => {
    if (!isCallActive) {
        isCallActive = true;
        callButton.classList.add('d-none');
        endCallButton.classList.remove('d-none');
        updateStatus('Call in progress...');
        recognition.start();
        speak('Hello, welcome to the Hospital. I’m here to assist with appointments or answer questions. How may I help you today?');
    }
});

endCallButton.addEventListener('click', () => {
    if (isCallActive) {
        isCallActive = false;
        recognition.stop();
        callButton.classList.remove('d-none');
        endCallButton.classList.add('d-none');
        updateStatus('Call ended.');
        speak('Thank you for calling. Goodbye.');
        conversationState = 'greeting';
        userData = { symptoms: '', name: '', time: '', department: '' };
        conversationHistory = [];
        appointmentSummary.classList.add('d-none');
    }
});