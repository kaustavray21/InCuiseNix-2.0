export const TutorAPI = {
    async startSession(payload) {
        const response = await fetch('/engine/api/tutor/start/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return await response.json();
    }
};