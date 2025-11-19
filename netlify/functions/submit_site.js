// Netlify serverless function to handle site submissions.
// Path: netlify/functions/submit_site.js

const fs = require('fs').promises;
const path = require('path');

// In a real application, the sites.json would be in a more persistent storage like a database
// or a repository that gets rebuilt and deployed. For this example, we'll simulate by writing
// to a file in a temporary directory, acknowledging Netlify's ephemeral filesystem.
const SITES_FILE_PATH = path.join('/tmp', 'sites.json');

async function readSites() {
    try {
        await fs.access(SITES_FILE_PATH);
        const data = await fs.readFile(SITES_FILE_PATH, 'utf-8');
        return JSON.parse(data);
    } catch (error) {
        // If the file doesn't exist or is invalid JSON, start with an empty array
        return [];
    }
}

async function writeSites(sites) {
    await fs.writeFile(SITES_FILE_PATH, JSON.stringify(sites, null, 2));
}

exports.handler = async (event, context) => {
    // Only allow POST requests
    if (event.httpMethod !== 'POST') {
        return {
            statusCode: 405,
            body: 'Method Not Allowed',
        };
    }

    try {
        const { name, site_id, description } = JSON.parse(event.body);

        // Basic validation
        if (!name || !site_id || !description) {
            return {
                statusCode: 400,
                body: JSON.stringify({ message: 'Missing required fields.' }),
            };
        }

        // Basic security scan simulation
        if (name.includes('<script>') || description.includes('<script>')) {
             return {
                statusCode: 400,
                body: JSON.stringify({ message: 'Malicious content detected.' }),
            };
        }

        const sites = await readSites();

        // Prevent duplicate site_id entries
        if (sites.some(site => site.site_id === site_id)) {
            return {
                statusCode: 409,
                body: JSON.stringify({ message: 'This site ID has already been submitted.' }),
            };
        }

        const newSite = {
            name,
            site_id,
            description,
            submitted_at: new Date().toISOString(),
        };

        sites.push(newSite);
        await writeSites(sites);

        return {
            statusCode: 200,
            body: JSON.stringify({ message: 'Site submitted successfully!' }),
        };

    } catch (error) {
        console.error('Error processing submission:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ message: 'An internal error occurred.' }),
        };
    }
};
