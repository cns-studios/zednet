// api/submit_site.js
const { Redis } = require("@upstash/redis");

export default async function handler(request, response) {
  // 1. Request Validation
  if (request.method !== "POST") {
    response.setHeader("Allow", ["POST"]);
    return response.status(405).json({ error: "Method Not Allowed" });
  }

  let newSite;
  try {
    // With Vercel, the body is automatically parsed if the content-type is correct.
    newSite = request.body;
    // Basic validation: ensure required fields are present.
    if (!newSite || !newSite.site_id || !newSite.name || !newSite.description) {
      throw new Error("Invalid site data: missing required fields.");
    }
  } catch (error) {
    return response.status(400).json({ error: "Bad Request: Invalid JSON or missing data." });
  }

  // 2. Database Connection
  try {
    const redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });

    // 3. Add to Database
    await redis.sadd("sites", JSON.stringify({
      name: newSite.name,
      site_id: newSite.site_id,
      description: newSite.description,
      added_ts: new Date().toISOString()
    }));

    // 4. Success Response
    response.setHeader("Access-Control-Allow-Origin", "*");
    return response.status(201).json({ message: "Site submitted successfully." });

  } catch (error) {
    console.error("Error submitting site to Upstash:", error);

    // 5. Error Response
    return response.status(500).json({ error: "Internal Server Error: Could not submit site." });
  }
}
