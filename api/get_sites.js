// api/get_sites.js
const { Redis } = require("@upstash/redis");

export default async function handler(request, response) {
  // Ensure the request is a GET request.
  if (request.method !== "GET") {
    response.setHeader("Allow", ["GET"]);
    return response.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    // Initialize the Redis client using environment variables.
    // These must be set in your Vercel project settings.
    const redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });

    // Fetch all members from the 'sites' set in Redis.
    const sitesJsonStrings = await redis.smembers("sites");

    // Parse the JSON strings back into objects.
    const sites = sitesJsonStrings.map(site => JSON.parse(site));

    // Set CORS headers and return the list of sites.
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Content-Type", "application/json");
    return response.status(200).json(sites);

  } catch (error) {
    // Log the error for debugging purposes.
    console.error("Error fetching sites from Upstash:", error);

    // Return a generic server error response.
    return response.status(500).json({ error: "Internal Server Error: Could not fetch site list." });
  }
}
