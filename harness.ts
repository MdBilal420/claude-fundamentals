import Anthropic from "@anthropic-ai/sdk";
import "dotenv/config";


const client = new Anthropic();

// LEVEL 1: Basic API call to generate a response from the model - NO HARNESS

// const res = await client.messages.create({
//   model: "claude-opus-4-6",
//   max_tokens: 4096,
//   messages: [{ role: "user", content: "Write a blog post" }],
// });
// const firstBlock = res.content[0];
// console.log(firstBlock && "text" in firstBlock ? firstBlock.text : "");

// LEVEL 2: Add tools (medium harness)
const tools = [
  {
    name: "read_existing_posts",
    description: "Return the list of existing blog posts with their titles",
    input_schema: { type: "object", properties: {} },
  },
  {
    name: "write_post",
    description: "Write out an MDX file",
    input_schema: {
      type: "object",
      properties: {
        slug: { type: "string" },
        frontmatter: { type: "object" },
        body: { type: "string" },
      },
      required: ["slug", "frontmatter", "body"],
    },
  },
];

async function runAgent(userGoal: string) {
  let messages = [{ role: "user", content: userGoal }];
  while (true) {
    const res = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 4096,
      tools,
      messages,
    });
    if (res.stop_reason === "end_turn") break;

    // The harness executes the tool call
    const toolUse = res.content.find((c) => c.type === "tool_use");
    const result = await executeTool(toolUse.name, toolUse.input);
    messages.push({ role: "assistant", content: res.content });
    messages.push({
      role: "user",
      content: [{ type: "tool_result", tool_use_id: toolUse.id, content: result }],
    });
  }
}

async function executeTool(name: string, input: any) {
  if (name === "read_existing_posts") {
    // In a real implementation, this would read from the filesystem or a database
    return [
      { title: "My First Blog Post" },
      { title: "How to Use the Anthropic API" },
    ];
  } else if (name === "write_post") {
    // In a real implementation, this would write to the filesystem or a database
    console.log("Writing post with slug:", input.slug);
    console.log("Frontmatter:", input.frontmatter);
    console.log("Body:", input.body);
    return { success: true };
  }
  throw new Error(`Unknown tool: ${name}`);
}

runAgent("Write a blog post about the benefits of using AI in software development.");


