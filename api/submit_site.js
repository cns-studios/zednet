// netlify/functions/submit_site.js
const { Redis } = require("@upstash/redis");

exports.handler = async function (event, context) {
  // 1. Request Validation
  if (event.httpMethod !== "POST") {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: "Method Not Allowed" }),
      headers: { "Content-Type": "application/json" },
    };
  }

  let newSite;
  try {
    newSite = JSON.parse(event.body);
    // Basic validation: ensure required fields are present.
    if (!newSite || !newSite.site_id || !newSite.name || !newSite.description) {
      throw new Error("Invalid site data: missing required fields.");
    }
  } catch (error) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: "Bad Request: Invalid JSON or missing data." }),
      headers: { "Content-Type": "application/json" },
    };
  }

  // 2. Database Connection
  try {
    const redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    });

    // 3. Add to Database
    // We store the site object as a JSON string in a Redis Set.
    // The Set automatically handles duplicates based on the string content.
    await redis.sadd("sites", JSON.stringify({
      name: newSite.name,
      site_id: newSite.site_id,
      description: newSite.description,
      // Add a timestamp for when it was added to the index.
      added_ts: new Date().toISOString()
    }));

    // 4. Success Response
    return {
      statusCode: 201, // 201 Created is more appropriate for a successful resource creation.
      body: JSON.stringify({ message: "Site submitted successfully." }),
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    };
  } catch (error) {
    console.error("Error submitting site to Upstash:", error);

    // 5. Error Response
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "Internal Server Error: Could not submit site." }),
      headers: { "Content-Type": "application/json" },
    };
  }
};
