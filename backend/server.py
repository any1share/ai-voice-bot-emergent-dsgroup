from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import json

# Import OpenAI Realtime and LlmChat from emergentintegrations
from emergentintegrations.llm.openai import OpenAIChatRealtime
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Get API key
api_key = os.environ.get('EMERGENT_LLM_KEY')

# Initialize OpenAI Realtime for voice
voice_chat = OpenAIChatRealtime(api_key=api_key)

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    system_prompt: str
    language: str = "hindi"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentCreate(BaseModel):
    name: str
    description: str
    system_prompt: str
    language: str = "hindi"

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None

class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str  # openai, anthropic, gemini
    api_key: str
    model_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str
    model_name: str

class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    agent_id: str
    role: str  # user or assistant
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    agent_id: str
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

# Register OpenAI Realtime router for voice
OpenAIChatRealtime.register_openai_realtime_router(api_router, voice_chat)

# Agent Management Endpoints
@api_router.post("/agents", response_model=Agent)
async def create_agent(agent_data: AgentCreate):
    """Create a new voice bot agent"""
    agent = Agent(**agent_data.model_dump())
    doc = agent.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.agents.insert_one(doc)
    return agent

@api_router.get("/agents", response_model=List[Agent])
async def get_agents():
    """Get all agents"""
    agents = await db.agents.find({}, {"_id": 0}).to_list(1000)
    for agent in agents:
        if isinstance(agent['created_at'], str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    return agents

@api_router.get("/agents/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str):
    """Get a specific agent by ID"""
    agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if isinstance(agent['created_at'], str):
        agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    return agent

@api_router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_update: AgentUpdate):
    """Update an agent"""
    existing_agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not existing_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = {k: v for k, v in agent_update.model_dump().items() if v is not None}
    if update_data:
        await db.agents.update_one({"id": agent_id}, {"$set": update_data})
    
    updated_agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if isinstance(updated_agent['created_at'], str):
        updated_agent['created_at'] = datetime.fromisoformat(updated_agent['created_at'])
    return updated_agent

@api_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    result = await db.agents.delete_one({"id": agent_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}

# LLM Configuration Endpoints
@api_router.post("/llm-configs", response_model=LLMConfig)
async def create_llm_config(config_data: LLMConfigCreate):
    """Create LLM configuration"""
    config = LLMConfig(**config_data.model_dump())
    doc = config.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.llm_configs.insert_one(doc)
    return config

@api_router.get("/llm-configs", response_model=List[LLMConfig])
async def get_llm_configs():
    """Get all LLM configurations"""
    configs = await db.llm_configs.find({}, {"_id": 0}).to_list(1000)
    for config in configs:
        if isinstance(config['created_at'], str):
            config['created_at'] = datetime.fromisoformat(config['created_at'])
    return configs

@api_router.delete("/llm-configs/{config_id}")
async def delete_llm_config(config_id: str):
    """Delete LLM configuration"""
    result = await db.llm_configs.delete_one({"id": config_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {"message": "Configuration deleted successfully"}

# Chat Endpoint (for text-based testing with Gemini)
@api_router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """Send a message to an agent using Gemini"""
    # Get agent details
    agent = await db.agents.find_one({"id": request.agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Create session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    # Initialize Gemini chat
    gemini_chat = LlmChat(
        api_key=api_key,
        session_id=session_id,
        system_message=agent['system_prompt']
    ).with_model("gemini", "gemini-2.0-flash")
    
    # Send message
    user_message = UserMessage(text=request.message)
    response = await gemini_chat.send_message(user_message)
    
    # Store conversation
    user_msg = ConversationMessage(
        session_id=session_id,
        agent_id=request.agent_id,
        role="user",
        content=request.message
    )
    assistant_msg = ConversationMessage(
        session_id=session_id,
        agent_id=request.agent_id,
        role="assistant",
        content=response
    )
    
    user_doc = user_msg.model_dump()
    user_doc['timestamp'] = user_doc['timestamp'].isoformat()
    assistant_doc = assistant_msg.model_dump()
    assistant_doc['timestamp'] = assistant_doc['timestamp'].isoformat()
    
    await db.conversations.insert_many([user_doc, assistant_doc])
    
    return ChatResponse(response=response, session_id=session_id)

# Initialize default order-taking agent
@app.on_event("startup")
async def startup_event():
    """Create default order-taking agent if not exists"""
    existing = await db.agents.find_one({"name": "Order Taking Agent"})
    if not existing:
        order_agent = Agent(
            name="Order Taking Agent",
            description="Hindi voice bot for taking customer orders",
            system_prompt="You are an order-taking voice bot that speaks in clear Hindi. Your job is to take orders from customers.\n\nInstructions:\n1. Always speak in clear and simple Hindi\n2. Let the customer speak - do not interrupt\n3. When customer says something, let them finish completely\n4. Listen patiently and understand\n5. Collect all information before confirming the order\n\nOrder taking process:\n1. Say Namaste and ask what they want to order\n2. Note the item name\n3. Ask for quantity\n4. Ask for delivery address\n5. Confirm contact number\n6. Repeat all order information\n7. Ask for confirmation\n\nRemember:\n- Speak in short sentences\n- Wait for customer response\n- Be polite and helpful\n- If you don't understand, ask again\n\nStart with: Namaste! Main aapke order mein madad karunga. Aap kya order karna chahte hain?",
            language="hindi"
        )
        doc = order_agent.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        await db.agents.insert_one(doc)
        logging.info("Default order-taking agent created")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
