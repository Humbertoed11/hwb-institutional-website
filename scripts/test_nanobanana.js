const { GoogleGenAI } = require('/home/humbertoed/.gemini/extensions/nanobanana/mcp-server/node_modules/@google/genai');

const apiKey = process.env.GEMINI_API_KEY;
console.log(`Testing with GEMINI_API_KEY (Length: ${apiKey ? apiKey.length : 'N/A'})`);

if (!apiKey) {
    console.error('Error: No API key found in environment');
    process.exit(1);
}

const ai = new GoogleGenAI({
    apiKey: apiKey,
});

async function test() {
    try {
        console.log('Attempting to verify key with gemini-1.5-flash-latest...');
        const response = await ai.models.generateContent({
            model: 'gemini-1.5-flash-latest',
            contents: [{ role: 'user', parts: [{ text: 'Hi' }] }]
        });
        
        console.log('Success! Key is working and connectivity is verified.');
    } catch (error) {
        console.error('Error during test:', error.message);
    }
}

test();
