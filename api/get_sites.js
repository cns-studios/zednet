// netlify/functions/get_sites.js
const { Redis } = require("@upstash/redis");

// This function is the main entry point for the Netlify serverless function.
exports.handler = async function (event, context) {
  // Ensure the request is a GET request.
  if (event.httpMethod !== "GET") {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: "Method Not Allowed" }),
      headers: { "Content-Type": "application/json" },
    };
  }

  try {
    // Initialize the Redis client using environment variables.
    // These must be set in your Netlify project settings.
    const redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });

    // Fetch all members from the 'sites' set in Redis.
    // Using a Set is ideal here to prevent duplicate site entries.
    const sitesJsonStrings = await redis.smembers("sites");

    // Parse the JSON strings back into objects.
    const sites = sitesJsonStrings.map(site => JSON.parse(site));

    // Return the list of sites with a success status code.
    return {
      statusCode: 200,
      body: JSON.stringify(sites),
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*", // Allow cross-origin requests
      },
    };
  } catch (error) {
    // Log the error for debugging purposes.
    console.error("Error fetching sites from Upstash:", error);

    // Return a generic server error response.
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal Server Error: Could not fetch site list." }),
      headers: { "Content-Type": "application/json" },
    };
  }
};
