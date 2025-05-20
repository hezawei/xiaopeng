import { request } from '@/utils'


// 需求分析 API
export const analyzeRequirements = async (requirements) => {
    try {
        const response = await request.post('/analyze', { content: requirements, source: 'user' });
        return response.data;
    } catch (error) {
        console.error('Error analyzing requirements:', error);
        throw error;
    }
};

// WebSocket 需求分析 API
export const createAnalysisWebSocket = (onMessage, onError) => {
    const ws = new WebSocket('ws://localhost:3100/ws/analyze');

    ws.onopen = () => {
        console.log('WebSocket connection established.');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.error) {
            onError(data.error);
        } else {
            onMessage(data.content);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError('WebSocket connection failed.');
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed.');
    };

    return {
        send: (requirements) => ws.send(JSON.stringify({ requirements })),
        close: () => ws.close(),
    };
};