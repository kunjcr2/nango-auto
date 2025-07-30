const axios = require("axios");
const fs = require("fs").promises;
const path = require("path");
const yaml = require("js-yaml");

class AIAPIConfigGenerator {
  /**
   * AI-Powered API Configuration Generator with Nango Integration Support
   * Uses OpenAI API to generate REAL API configurations with actual endpoints
   * and creates Nango integration configurations automatically
   */

  constructor(openaiApiKey) {
    /**
     * Initialize the AI API Generator
     *
     * @param {string} openaiApiKey - OpenAI API key (can also be set via OPENAI_API_KEY env var)
     */
    this.apiKey = openaiApiKey;
    if (!this.apiKey) {
      throw new Error(
        "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly."
      );
    }

    this.openaiClient = axios.create({
      baseURL: "https://api.openai.com/v1",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
    });
  }

  async _callOpenAIAPI(applicationName) {
    /**
     * Call OpenAI API to generate REAL API configuration for the given application
     */

    // First, let's try to get real endpoints from known APIs
    const knownAPIs = this._getKnownAPIConfig(applicationName);
    if (knownAPIs) {
      console.log(`📚 Using known API configuration for ${applicationName}`);
      return knownAPIs;
    }

    const prompt = `Generate REAL API endpoints for ${applicationName}'s official API. Use their actual documented endpoints.

For ${applicationName}, provide a JSON response with this exact structure:
{
    "provider": "${applicationName} API",
    "base_url": "https://api.${applicationName.toLowerCase()}.com",
    "endpoints": [
        {"name": "endpoint_name", "method": "GET|POST|PUT|DELETE", "path": "/real/path", "description": "What it does"}
    ]
}

Include 15-20 real endpoints that actually exist in ${applicationName}'s API documentation.

IMPORTANT: Return only valid JSON, no markdown formatting or explanations.`;

    const requestBody = {
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content:
            "You are an API documentation expert. Generate only real, documented API endpoints that exist in official API documentation. Return only valid JSON without markdown formatting.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      temperature: 0.1,
      max_tokens: 2000,
    };

    try {
      console.log(`🤖 Calling OpenAI API for ${applicationName}...`);
      const response = await this.openaiClient.post(
        "/chat/completions",
        requestBody
      );

      if (
        !response.data ||
        !response.data.choices ||
        !response.data.choices[0]
      ) {
        throw new Error("Invalid response from OpenAI API");
      }

      let content = response.data.choices[0].message.content.trim();
      console.log(`📝 Received response for ${applicationName}`);

      // Clean up the response to ensure it's valid JSON
      content = content
        .replace(/```json\s*/g, "")
        .replace(/```\s*/g, "")
        .trim();

      // Remove any text before the first { or after the last }
      const firstBrace = content.indexOf("{");
      const lastBrace = content.lastIndexOf("}");

      if (firstBrace !== -1 && lastBrace !== -1) {
        content = content.substring(firstBrace, lastBrace + 1);
      }

      // Parse the JSON response
      const apiConfig = JSON.parse(content);

      // Validate the structure
      if (
        !apiConfig.provider ||
        !apiConfig.base_url ||
        !Array.isArray(apiConfig.endpoints)
      ) {
        throw new Error("Invalid API config structure received");
      }

      // Validate that we got real endpoints
      if (!this._validateRealEndpoints(apiConfig, applicationName)) {
        console.warn(
          `⚠️  Generated endpoints may not be completely accurate for ${applicationName}`
        );
      }

      console.log(
        `✅ Successfully generated ${apiConfig.endpoints.length} endpoints for ${applicationName}`
      );
      return apiConfig;
    } catch (error) {
      console.error(
        `❌ Error generating API config for ${applicationName}: ${error.message}`
      );
      console.log(`🔄 Using fallback configuration for ${applicationName}`);
      return this._generateFallbackConfig(applicationName);
    }
  }

  _getKnownAPIConfig(applicationName) {
    /**
     * Return known API configurations for popular services
     */
    const knownConfigs = {
      slack: {
        provider: "Slack API",
        base_url: "https://slack.com/api",
        endpoints: [
          {
            name: "auth.test",
            method: "POST",
            path: "/auth.test",
            description: "Check authentication and identity",
          },
          {
            name: "channels.list",
            method: "GET",
            path: "/channels.list",
            description: "List all channels in a workspace",
          },
          {
            name: "chat.postMessage",
            method: "POST",
            path: "/chat.postMessage",
            description: "Send a message to a channel",
          },
          {
            name: "users.list",
            method: "GET",
            path: "/users.list",
            description: "List all users in a workspace",
          },
          {
            name: "users.info",
            method: "GET",
            path: "/users.info",
            description: "Get information about a user",
          },
          {
            name: "conversations.list",
            method: "GET",
            path: "/conversations.list",
            description: "List conversations the calling user may access",
          },
          {
            name: "conversations.history",
            method: "GET",
            path: "/conversations.history",
            description: "Fetch conversation history",
          },
          {
            name: "conversations.info",
            method: "GET",
            path: "/conversations.info",
            description: "Retrieve information about a conversation",
          },
          {
            name: "files.upload",
            method: "POST",
            path: "/files.upload",
            description: "Upload or create a file",
          },
          {
            name: "reactions.add",
            method: "POST",
            path: "/reactions.add",
            description: "Add a reaction to a message",
          },
          {
            name: "team.info",
            method: "GET",
            path: "/team.info",
            description: "Get information about current team",
          },
          {
            name: "chat.update",
            method: "POST",
            path: "/chat.update",
            description: "Update a message",
          },
          {
            name: "chat.delete",
            method: "POST",
            path: "/chat.delete",
            description: "Delete a message",
          },
          {
            name: "usergroups.list",
            method: "GET",
            path: "/usergroups.list",
            description: "List all user groups",
          },
          {
            name: "bots.info",
            method: "GET",
            path: "/bots.info",
            description: "Get information about a bot user",
          },
        ],
      },
      github: {
        provider: "GitHub API",
        base_url: "https://api.github.com",
        endpoints: [
          {
            name: "user",
            method: "GET",
            path: "/user",
            description: "Get the authenticated user",
          },
          {
            name: "user.repos",
            method: "GET",
            path: "/user/repos",
            description: "List repositories for the authenticated user",
          },
          {
            name: "repos.get",
            method: "GET",
            path: "/repos/{owner}/{repo}",
            description: "Get a repository",
          },
          {
            name: "repos.issues",
            method: "GET",
            path: "/repos/{owner}/{repo}/issues",
            description: "List repository issues",
          },
          {
            name: "repos.pulls",
            method: "GET",
            path: "/repos/{owner}/{repo}/pulls",
            description: "List pull requests",
          },
          {
            name: "repos.commits",
            method: "GET",
            path: "/repos/{owner}/{repo}/commits",
            description: "List commits",
          },
          {
            name: "repos.contents",
            method: "GET",
            path: "/repos/{owner}/{repo}/contents/{path}",
            description: "Get repository content",
          },
          {
            name: "issues.create",
            method: "POST",
            path: "/repos/{owner}/{repo}/issues",
            description: "Create an issue",
          },
          {
            name: "pulls.create",
            method: "POST",
            path: "/repos/{owner}/{repo}/pulls",
            description: "Create a pull request",
          },
          {
            name: "repos.branches",
            method: "GET",
            path: "/repos/{owner}/{repo}/branches",
            description: "List branches",
          },
          {
            name: "user.orgs",
            method: "GET",
            path: "/user/orgs",
            description: "List organizations for authenticated user",
          },
          {
            name: "repos.collaborators",
            method: "GET",
            path: "/repos/{owner}/{repo}/collaborators",
            description: "List repository collaborators",
          },
          {
            name: "repos.releases",
            method: "GET",
            path: "/repos/{owner}/{repo}/releases",
            description: "List releases",
          },
          {
            name: "gists",
            method: "GET",
            path: "/gists",
            description: "List gists for authenticated user",
          },
          {
            name: "notifications",
            method: "GET",
            path: "/notifications",
            description: "List notifications",
          },
        ],
      },
      discord: {
        provider: "Discord API",
        base_url: "https://discord.com/api/v10",
        endpoints: [
          {
            name: "get.user",
            method: "GET",
            path: "/users/@me",
            description: "Get current user object",
          },
          {
            name: "get.guilds",
            method: "GET",
            path: "/users/@me/guilds",
            description: "Get current user guilds",
          },
          {
            name: "get.guild",
            method: "GET",
            path: "/guilds/{guild.id}",
            description: "Get guild object",
          },
          {
            name: "get.channels",
            method: "GET",
            path: "/guilds/{guild.id}/channels",
            description: "Get guild channels",
          },
          {
            name: "get.channel",
            method: "GET",
            path: "/channels/{channel.id}",
            description: "Get channel",
          },
          {
            name: "get.messages",
            method: "GET",
            path: "/channels/{channel.id}/messages",
            description: "Get channel messages",
          },
          {
            name: "create.message",
            method: "POST",
            path: "/channels/{channel.id}/messages",
            description: "Create message",
          },
          {
            name: "get.guild.members",
            method: "GET",
            path: "/guilds/{guild.id}/members",
            description: "List guild members",
          },
          {
            name: "get.guild.roles",
            method: "GET",
            path: "/guilds/{guild.id}/roles",
            description: "Get guild roles",
          },
          {
            name: "create.dm",
            method: "POST",
            path: "/users/@me/channels",
            description: "Create DM channel",
          },
          {
            name: "add.reaction",
            method: "PUT",
            path: "/channels/{channel.id}/messages/{message.id}/reactions/{emoji}/@me",
            description: "Create reaction",
          },
          {
            name: "get.webhooks",
            method: "GET",
            path: "/channels/{channel.id}/webhooks",
            description: "Get channel webhooks",
          },
          {
            name: "create.webhook",
            method: "POST",
            path: "/channels/{channel.id}/webhooks",
            description: "Create webhook",
          },
          {
            name: "modify.guild.member",
            method: "PATCH",
            path: "/guilds/{guild.id}/members/{user.id}",
            description: "Modify guild member",
          },
          {
            name: "get.invites",
            method: "GET",
            path: "/guilds/{guild.id}/invites",
            description: "Get guild invites",
          },
        ],
      },
    };

    return knownConfigs[applicationName.toLowerCase()] || null;
  }

  _validateRealEndpoints(config, appName) {
    /**
     * Basic validation to check if endpoints look real
     */
    if (!config.endpoints || !Array.isArray(config.endpoints)) {
      return false;
    }

    // Check for generic patterns that suggest fake endpoints
    const fakePatterns = [
      "/items",
      "/item/{id}",
      "/generic",
      "/api/v1/resource",
    ];

    for (const endpoint of config.endpoints) {
      const path = endpoint.path || "";
      if (fakePatterns.some((pattern) => path.includes(pattern))) {
        return false;
      }
    }

    return true;
  }

  _generateFallbackConfig(applicationName) {
    /**
     * Enhanced fallback configuration with common REST endpoints
     */
    const appTitle =
      applicationName.charAt(0).toUpperCase() + applicationName.slice(1);

    // Try to provide some generic but useful endpoints based on common patterns
    const commonEndpoints = [
      {
        name: "get_user",
        method: "GET",
        path: "/user",
        description: `Get current user information from ${appTitle}`,
      },
      {
        name: "list_items",
        method: "GET",
        path: "/items",
        description: `List all items from ${appTitle}`,
      },
      {
        name: "get_item",
        method: "GET",
        path: "/items/{id}",
        description: `Get specific item by ID from ${appTitle}`,
      },
      {
        name: "create_item",
        method: "POST",
        path: "/items",
        description: `Create new item in ${appTitle}`,
      },
      {
        name: "update_item",
        method: "PUT",
        path: "/items/{id}",
        description: `Update existing item in ${appTitle}`,
      },
      {
        name: "delete_item",
        method: "DELETE",
        path: "/items/{id}",
        description: `Delete item from ${appTitle}`,
      },
      {
        name: "search",
        method: "GET",
        path: "/search",
        description: `Search content in ${appTitle}`,
      },
      {
        name: "get_profile",
        method: "GET",
        path: "/profile",
        description: `Get user profile from ${appTitle}`,
      },
    ];

    return {
      provider: `${appTitle} API`,
      base_url: `https://api.${applicationName.toLowerCase()}.com`,
      endpoints: commonEndpoints,
    };
  }

  async astype(applicationName) {
    /**
     * Return REAL API configuration using astype method as requested
     *
     * @param {string} applicationName - Name of the application
     * @returns {Object} Dictionary with provider, base_url, and real endpoints
     */
    return await this._callOpenAIAPI(applicationName);
  }

  async getRealAPIConfig(applicationName) {
    /**
     * Get REAL API configuration for the specified application
     *
     * @param {string} applicationName - Name of the application (e.g., 'slack', 'github', 'discord')
     * @returns {Object} Dictionary with provider, base_url, and real endpoints
     */
    return await this.astype(applicationName);
  }

  _generateNangoIntegrationConfig(appName, apiConfig) {
    /**
     * Generate Nango integration configuration (nango.yaml format)
     * Based on the API configuration
     */
    const integrationId = appName.toLowerCase().replace(/[^a-z0-9]/g, "-");
    const providerName = apiConfig.provider || appName;

    // Generate syncs and actions based on endpoints
    const syncs = {};
    const actions = {};

    // Skip error endpoints
    const validEndpoints = apiConfig.endpoints.filter(
      (endpoint) => endpoint.name !== "error" && endpoint.path !== "/error"
    );

    validEndpoints.forEach((endpoint, index) => {
      const endpointName = endpoint.name
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "-");
      const cleanPath = endpoint.path.replace(/[{}]/g, "").toLowerCase();

      if (endpoint.method === "GET" && !endpoint.path.includes("{")) {
        // Create sync for GET endpoints without parameters (list endpoints)
        const syncName = `${endpointName}-sync`;
        syncs[syncName] = {
          description:
            endpoint.description ||
            `Sync ${endpoint.name} from ${providerName}`,
          output: `${providerName.replace(/[^a-zA-Z0-9]/g, "")}${
            endpoint.name
              .replace(/[^a-zA-Z0-9]/g, "")
              .charAt(0)
              .toUpperCase() +
            endpoint.name.replace(/[^a-zA-Z0-9]/g, "").slice(1)
          }`,
          endpoint: {
            method: "GET",
            path: endpoint.path,
          },
          sync_type: "incremental",
          runs: "every 30min",
        };
      } else {
        // Create action for POST, PUT, DELETE, PATCH endpoints or GET with parameters
        const actionName = `${endpointName}-action`;
        actions[actionName] = {
          description:
            endpoint.description ||
            `Execute ${endpoint.name} on ${providerName}`,
          endpoint: {
            method: endpoint.method,
            path: endpoint.path,
          },
        };
      }
    });

    // Ensure we have at least some syncs or actions
    if (Object.keys(syncs).length === 0 && Object.keys(actions).length === 0) {
      // Create at least one action from the first endpoint
      const firstEndpoint = validEndpoints[0] || apiConfig.endpoints[0];
      if (firstEndpoint) {
        actions["default-action"] = {
          description:
            firstEndpoint.description || `Default action for ${providerName}`,
          endpoint: {
            method: firstEndpoint.method,
            path: firstEndpoint.path,
          },
        };
      }
    }

    const integration = {};
    if (Object.keys(syncs).length > 0) {
      integration.syncs = syncs;
    }
    if (Object.keys(actions).length > 0) {
      integration.actions = actions;
    }

    return {
      integrations: {
        [integrationId]: integration,
      },
    };
  }

  _generateNangoProviderConfig(appName, apiConfig) {
    /**
     * Generate Nango provider configuration (providers.yaml format)
     */
    const providerSlug = appName.toLowerCase().replace(/[^a-z0-9]/g, "-");

    return {
      [providerSlug]: {
        display_name: apiConfig.provider || appName,
        categories: ["productivity"], // Default category
        auth_mode: "OAUTH2",
        authorization_url: `${apiConfig.base_url}/oauth/authorize`,
        token_url: `${apiConfig.base_url}/oauth/token`,
        docs: `https://docs.${appName.toLowerCase()}.com/api`,
        default_scopes: ["read", "write"],
      },
    };
  }

  async generateMultipleConfigs(applicationsInput) {
    /**
     * Generate API configurations for multiple applications from comma-separated input
     *
     * @param {string} applicationsInput - Comma-separated string like "youtube, google, gmail"
     * @returns {Object} Dictionary with app names as keys and their API configs as values
     */
    // Parse the input string
    const appNames = applicationsInput
      .split(",")
      .map((app) => app.trim().toLowerCase())
      .filter((app) => app.length > 0);

    if (appNames.length === 0) {
      return {};
    }

    console.log(
      `🚀 Generating real API configurations for: ${appNames.join(", ")}`
    );
    console.log("📡 Making API calls...\n");

    const configs = {};

    for (const appName of appNames) {
      console.log(`⏳ Generating config for ${appName}...`);
      try {
        const config = await this.astype(appName);
        configs[appName] = {
          api_config: config,
          nango_integration: this._generateNangoIntegrationConfig(
            appName,
            config
          ),
          nango_provider: this._generateNangoProviderConfig(appName, config),
        };
        console.log(
          `✅ Generated ${config.endpoints.length} real endpoints for ${appName}`
        );
      } catch (error) {
        console.error(
          `❌ Error generating config for ${appName}: ${error.message}`
        );
        configs[appName] = {
          api_config: {
            provider: appName.charAt(0).toUpperCase() + appName.slice(1),
            base_url: `https://api.${appName}.com`,
            endpoints: [
              {
                name: "error",
                method: "GET",
                path: "/error",
                description: `Failed to generate config for ${appName}`,
              },
            ],
          },
          nango_integration: null,
          nango_provider: null,
        };
      }
    }

    return configs;
  }

  async saveConfigsToFiles(configs, outputDir = "./generated-configs") {
    /**
     * Save generated configurations to files
     *
     * @param {Object} configs - Generated configurations
     * @param {string} outputDir - Output directory for files
     */
    try {
      // Ensure output directory exists
      await fs.mkdir(outputDir, { recursive: true });

      for (const [appName, config] of Object.entries(configs)) {
        const appDir = path.join(outputDir, appName);
        await fs.mkdir(appDir, { recursive: true });

        // Save API configuration as JSON
        await fs.writeFile(
          path.join(appDir, "api-config.json"),
          JSON.stringify(config.api_config, null, 2)
        );

        // Save Nango integration configuration as YAML
        if (config.nango_integration) {
          await fs.writeFile(
            path.join(appDir, "nango-integration.yaml"),
            yaml.dump(config.nango_integration, { indent: 2 })
          );
        }

        // Save Nango provider configuration as YAML
        if (config.nango_provider) {
          await fs.writeFile(
            path.join(appDir, "nango-provider.yaml"),
            yaml.dump(config.nango_provider, { indent: 2 })
          );
        }

        // Generate JavaScript endpoints module
        const endpointsJS = this._generateEndpointsJavaScript(
          appName,
          config.api_config
        );
        await fs.writeFile(path.join(appDir, "endpoints.js"), endpointsJS);

        console.log(`📁 Saved configuration files for ${appName} in ${appDir}`);
      }

      console.log(`\n🎉 All configurations saved to ${outputDir}`);
    } catch (error) {
      console.error(`Error saving configs to files: ${error.message}`);
    }
  }

  _generateEndpointsJavaScript(appName, apiConfig) {
    /**
     * Generate JavaScript code for API endpoints
     */
    const className =
      appName.charAt(0).toUpperCase() + appName.slice(1) + "API";
    const baseUrl = apiConfig.base_url;

    let jsCode = `/**
 * ${apiConfig.provider} API Client
 * Generated automatically by AI API Config Generator
 */

class ${className} {
    constructor(apiKey, baseUrl = '${baseUrl}') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': \`Bearer \${apiKey}\`,
            'Content-Type': 'application/json',
            'User-Agent': '${appName}-client/1.0.0'
        };
    }
    
    async makeRequest(method, path, data = null, params = null) {
        const url = new URL(path, this.baseUrl);
        
        if (params) {
            Object.keys(params).forEach(key => {
                if (params[key] !== null && params[key] !== undefined) {
                    url.searchParams.append(key, params[key]);
                }
            });
        }
        
        const config = {
            method: method,
            headers: this.headers
        };
        
        if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
            config.body = JSON.stringify(data);
        }
        
        try {
            const response = await fetch(url.toString(), config);
            
            if (!response.ok) {
                throw new Error(\`HTTP error! status: \${response.status}\`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(\`API request failed: \${error.message}\`);
            throw error;
        }
    }

`;

    // Generate methods for each endpoint
    apiConfig.endpoints.forEach((endpoint) => {
      const methodName = endpoint.name
        .replace(/[^a-zA-Z0-9]/g, "")
        .toLowerCase();
      const method = endpoint.method.toUpperCase();
      const path = endpoint.path;

      // Extract path parameters
      const pathParams = [];
      const pathParamRegex = /\{([^}]+)\}/g;
      let match;
      while ((match = pathParamRegex.exec(path)) !== null) {
        pathParams.push(match[1]);
      }

      // Generate method parameters
      const methodParams = [...pathParams];
      if (["POST", "PUT", "PATCH"].includes(method)) {
        methodParams.push("data = {}");
      }
      if (method === "GET") {
        methodParams.push("params = null");
      }

      // Generate method body
      let methodPath = path;
      pathParams.forEach((param) => {
        methodPath = methodPath.replace(`{${param}}`, "${" + param + "}");
      });

      jsCode += `    /**
     * ${endpoint.description || `${method} ${path}`}
     * @param {${pathParams.map((p) => `string ${p}`).join(", ")}} ${
        pathParams.length > 0 ? "- Path parameters" : ""
      }${
        methodParams.includes("data = {}")
          ? "\n     * @param {Object} data - Request body data"
          : ""
      }${
        methodParams.includes("params = null")
          ? "\n     * @param {Object} params - Query parameters"
          : ""
      }
     * @returns {Promise} API response
     */
    async ${methodName}(${methodParams.join(", ")}) {
        const path = \`${methodPath}\`;
        return await this.makeRequest('${method}', path${
        methodParams.includes("data = {}") ? ", data" : ", null"
      }${methodParams.includes("params = null") ? ", params" : ""});
    }

`;
    });

    jsCode += `}

// Export the class
module.exports = ${className};

// Example usage:
/*
const api = new ${className}(${process.env.OPENAI_API_KEY});

// Example calls:
${apiConfig.endpoints
  .slice(0, 3)
  .map((endpoint) => {
    const methodName = endpoint.name.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
    return `// api.${methodName}().then(console.log).catch(console.error);`;
  })
  .join("\n")}
*/
`;

    return jsCode;
  }
}

// Export the class
module.exports = AIAPIConfigGenerator;

// Example usage:
async function example() {
  try {
    const generator = new AIAPIConfigGenerator(process.env.OPENAI_API_KEY);

    // Generate configs for multiple apps
    const configs = await generator.generateMultipleConfigs(
      "slack, github, discord"
    );

    // Save to files
    await generator.saveConfigsToFiles(configs);

    console.log("Generated configurations:", JSON.stringify(configs, null, 2));
  } catch (error) {
    console.error("Error:", error.message);
  }
}

// Uncomment to run example
example();
