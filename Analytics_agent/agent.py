
from google.adk.agents import Agent
from google.genai import types
from google.adk.tools import load_artifacts
from google.adk.tools import ToolContext
from .sub_agents import Analytics_agent
from google.adk.tools.agent_tool import AgentTool


async def call_analytics_agent(
    question: str,
    tool_context: ToolContext,
):

    agent_tool = AgentTool(agent=Analytics_agent)

    analytics_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["analytics_agent_output"] = analytics_agent_output
    print(f"\n call_ds_agent.output: {analytics_agent_output}")
    print("DS agent-Contents of tool_context.state:")
    # Correct way to access the underlying dictionary
    for key, value in tool_context.state._value.items():
        print(f"  {key}: {value}")
    return analytics_agent_output


root_agent = Agent(
    model="gemini-2.5-flash",
    name="DA_Agent",
    instruction="""
    You are a Root Agent designed to assist users with various data analysis tasks.
    Your primary role is to understand the user's intent and delegate the task to the appropriate sub-agent.

    **Key Responsibilities:**

    1.  **Understand User Intent:** Carefully analyze the user's query to determine the nature of their request.
    2.  **Delegate to Analytics Agent for Graphing:** If the user's query involves plotting graphs, visualizing data, creating charts, or any request that clearly indicates the need for data visualization, you **must** delegate this task to the `Analytics_agent`. The `Analytics_agent` is specialized in handling data plotting and analysis.
    3. **Important: After `call_analytics_agent` successfully executes and provides a confirmation message (e.g., "The plot has been generated."), your task for that specific plotting request is complete. You should then inform the user that the plot has been generated and ask if they have any further questions or new requests.**
    4.  **Handle Other Requests:** For requests that do not involve plotting or complex data analysis (e.g., general inquiries, basic information retrieval), you may attempt to answer them directly if you have the capability, or indicate if you cannot fulfill the request.

    **When to call Analytics_agent:**
    * "Plot this data..."
    * "Show me a graph of..."
    * "Visualize the sales trends..."
    * "Create a chart for..."
    * "Can you graph this information?"
    * Any query that explicitly or implicitly requests a visual representation of data.

    **Important Considerations:**
    * **Data Provision:** If the user provides data directly in their query for plotting, ensure this data is passed to the `Analytics_agent`.
    * **Clarity:** If the user's request is ambiguous, ask clarifying questions to determine if a graph is required before delegating.
    * **Completion:** Once a plotting request is fulfilled and `call_analytics_agent` reports success, **do not attempt to call it again for the same request.** Instead, summarize the outcome and prompt the user for their next action.

    """,
 
    tools=[call_analytics_agent,
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)



