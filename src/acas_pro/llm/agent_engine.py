#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Agent Engine
Autonomous agent execution with LLM reasoning
"""

import json
import time
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import threading
from queue import Queue

from .llm_client import LLMClient, LLMMessage, LLMResponse, LLMConfig


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ActionType(Enum):
    """Action types"""
    THINK = "think"
    USE_TOOL = "use_tool"
    RESPOND = "respond"
    WAIT = "wait"
    STOP = "stop"
    ERROR = "error"


@dataclass
class AgentTask:
    """Agent task definition"""
    id: str
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    max_steps: int = 10
    priority: int = 0  # 0=highest
    created_at: float = field(default_factory=time.time)
    timeout_seconds: int = 300


@dataclass
class AgentAction:
    """Agent action record"""
    type: ActionType
    content: str = ""
    tool_name: str = ""
    tool_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Agent execution result"""
    task_id: str
    status: AgentStatus
    actions: List[AgentAction] = field(default_factory=list)
    final_response: str = ""
    total_tokens: int = 0
    total_time_ms: int = 0
    error: str = ""


class AgentEngine:
    """
    Autonomous Agent Engine
    Enables LLM to autonomously execute tasks in ACAS Pro
    """
    
    # System prompt for ACAS Pro agent
    SYSTEM_PROMPT = """You are ACAS Agent, an autonomous AI assistant integrated into ACAS Pro (Intelligent Customer Acquisition System).

Your capabilities include:
- Sales forecasting and prediction analysis
- Inventory optimization recommendations  
- Market intelligence and sentiment analysis
- Content creation and trend monitoring
- Account management across platforms
- Video production and publishing
- Ad campaign management
- E-commerce operations
- Blockchain settlement tracking

When asked to perform tasks:
1. Think through the task requirements
2. Use available tools to gather information or perform actions
3. Provide clear, actionable results
4. Ask for clarification if needed

Always respond in Chinese (简体中文) unless the user asks in another language.

Available tools will be provided in the conversation. Use them when appropriate."""

    def __init__(self, llm_client: LLMClient, tools_registry: "ToolRegistry" = None):
        self.llm = llm_client
        self.tools_registry = tools_registry
        self.status = AgentStatus.IDLE
        self._current_task: Optional[AgentTask] = None
        self._action_history: List[AgentAction] = []
        self._stop_flag = False
        self._message_queue: Queue = Queue()
    
    def execute(self, task: AgentTask) -> AgentResult:
        """
        Execute a task autonomously
        Returns the final result after completion
        """
        self.status = AgentStatus.THINKING
        self._current_task = task
        self._stop_flag = False
        self._action_history = []
        
        start_time = time.time()
        total_tokens = 0
        final_response = ""
        error = ""
        
        try:
            # Build initial messages
            messages = self._build_messages(task)
            
            # Get available tools
            tools = self._get_tools_schema(task.tools) if self.tools_registry else None
            
            step = 0
            while step < task.max_steps and not self._stop_flag:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > task.timeout_seconds:
                    self.status = AgentStatus.FAILED
                    error = f"Task timed out after {task.timeout_seconds}s ({elapsed:.1f}s elapsed)"
                    final_response = f"执行超时: {error}"
                    break

                self.status = AgentStatus.THINKING
                
                # Call LLM
                response = self.llm.chat(messages, tools=tools)
                total_tokens += response.usage.get('total_tokens', 0)
                
                # Record action
                action = AgentAction(
                    type=ActionType.THINK,
                    content=response.content,
                    reasoning=f"Step {step + 1}: LLM reasoning"
                )
                self._action_history.append(action)
                
                # Check for tool calls
                if response.tool_calls:
                    self.status = AgentStatus.EXECUTING
                    
                    # Process each tool call
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['function']['name']
                        tool_args = json.loads(tool_call['function']['arguments'])
                        
                        # Record tool action
                        tool_action = AgentAction(
                            type=ActionType.USE_TOOL,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            reasoning=f"Executing tool: {tool_name}"
                        )
                        
                        # Execute tool
                        try:
                            result = self._execute_tool(tool_name, tool_args)
                            tool_action.result = result
                        except Exception as e:
                            import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))
                            tool_action.result = {"error": str(e)}
                            tool_action.type = ActionType.ERROR
                        
                        self._action_history.append(tool_action)
                        
                        # Add tool result to messages
                        messages.append(LLMMessage(
                            role="assistant",
                            content="",
                            tool_calls=[tool_call]
                        ))
                        messages.append(LLMMessage(
                            role="tool",
                            content=json.dumps(tool_action.result),
                            tool_call_id=tool_call['id']
                        ))
                else:
                    # No tool calls - check if done
                    final_response = response.content
                    
                    # Add assistant message
                    messages.append(LLMMessage(role="assistant", content=response.content))
                    
                    # Check finish reason
                    if response.finish_reason == "stop":
                        self.status = AgentStatus.COMPLETED
                        break
                    elif response.finish_reason == "length":
                        # Continue but note we hit length limit
                        messages.append(LLMMessage(
                            role="user",
                            content="请继续..."
                        ))
                    else:
                        self.status = AgentStatus.COMPLETED
                        break
                
                step += 1
            
            if step >= task.max_steps:
                self.status = AgentStatus.COMPLETED
                final_response = f"[达到最大步骤限制 {task.max_steps}]\n\n{final_response}"
            
        except Exception as e:
            import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))
            self.status = AgentStatus.FAILED
            error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            final_response = f"执行失败: {error}"
        
        finally:
            total_time_ms = int((time.time() - start_time) * 1000)
            self._current_task = None
            if self._stop_flag:
                self.status = AgentStatus.STOPPED
        
        return AgentResult(
            task_id=task.id,
            status=self.status,
            actions=self._action_history.copy(),
            final_response=final_response,
            total_tokens=total_tokens,
            total_time_ms=total_time_ms,
            error=error
        )
    
    def execute_async(self, task: AgentTask, callback: Callable[[AgentResult], None] = None) -> threading.Thread:
        """Execute task asynchronously"""
        # Defensive: ensure task is an AgentTask object
        if isinstance(task, str):
            task = AgentTask(prompt=task)
        
        def _run() -> None:
            try:
                result = self.execute(task)
                if callback:
                    callback(result)
            except Exception as e:
                logger.error(f"Async agent execution failed: {e}")
        
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
    
    def stop(self) -> None:
        """Stop current execution"""
        self._stop_flag = True
        self.status = AgentStatus.STOPPED
    
    def get_status(self) -> AgentStatus:
        """Get current status"""
        return self.status
    
    def get_action_history(self) -> List[AgentAction]:
        """Get action history"""
        return self._action_history.copy()
    
    def _build_messages(self, task: AgentTask) -> List[LLMMessage]:
        """Build initial messages from task"""
        messages = [
            LLMMessage(role="system", content=self.SYSTEM_PROMPT)
        ]
        
        # Add context if provided
        if task.context:
            context_str = json.dumps(task.context, ensure_ascii=False, indent=2)
            messages.append(LLMMessage(
                role="system",
                content=f"当前上下文数据:\n```json\n{context_str}\n```"
            ))
        
        # Add task prompt
        messages.append(LLMMessage(role="user", content=task.prompt))
        
        return messages
    
    def _get_tools_schema(self, tool_names: List[str]) -> List[Dict]:
        """Get OpenAI-compatible tools schema"""
        if not self.tools_registry:
            return []
        
        if not tool_names:
            # Return all tools
            return self.tools_registry.get_all_schemas()
        
        return [self.tools_registry.get_schema(name) for name in tool_names if name]
    
    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool by name"""
        if not self.tools_registry:
            raise RuntimeError("No tools registry configured")
        
        return self.tools_registry.execute(name, **args)


class AgentOrchestrator:
    """
    Multi-agent orchestrator for complex tasks
    Coordinates multiple agents for parallel or sequential execution
    """
    
    def __init__(self, llm_config: LLMConfig, tools_registry: "ToolRegistry" = None):
        self.llm_config = llm_config
        self.tools_registry = tools_registry
        self._agents: Dict[str, AgentEngine] = {}
        self._results: Dict[str, AgentResult] = {}
    
    def create_agent(self, agent_id: str, specialty: str = "") -> AgentEngine:
        """Create a new agent"""
        llm_client = LLMClient(self.llm_config)
        agent = AgentEngine(llm_client, self.tools_registry)
        
        # Customize system prompt for specialty
        if specialty:
            agent.SYSTEM_PROMPT = f"{AgentEngine.SYSTEM_PROMPT}\n\n你的专长是: {specialty}"
        
        self._agents[agent_id] = agent
        return agent
    
    def execute_parallel(self, tasks: List[AgentTask], agent_ids: List[str] = None,
                         timeout_per_task: float = None) -> Dict[str, AgentResult]:
        """Execute multiple tasks in parallel

        Args:
            tasks: List of tasks to execute
            agent_ids: Optional list of agent IDs to use
            timeout_per_task: Max seconds per task (default: uses task.timeout_seconds)
        """
        results = {}
        threads = []

        for i, task in enumerate(tasks):
            agent_id = agent_ids[i] if agent_ids and i < len(agent_ids) else f"agent_{i}"

            if agent_id not in self._agents:
                self.create_agent(agent_id)

            agent = self._agents[agent_id]

            def _run(tid, t, a) -> None:
                results[tid] = a.execute(t)

            thread = threading.Thread(target=_run, args=(task.id, task, agent))
            threads.append(thread)
            thread.start()

        # Join with timeout to avoid blocking forever
        timeout = timeout_per_task or max(t.timeout_seconds for t in tasks) if tasks else 300
        for thread in threads:
            thread.join(timeout=timeout + 30)  # extra buffer for cleanup

        return results
    
    def execute_pipeline(self, tasks: List[AgentTask], pass_results: bool = True) -> List[AgentResult]:
        """Execute tasks sequentially, passing results forward"""
        results = []
        context = {}
        
        for i, task in enumerate(tasks):
            # Create agent for this step
            agent_id = f"pipeline_step_{i}"
            agent = self.create_agent(agent_id) if agent_id not in self._agents else self._agents[agent_id]
            
            # Add previous results to context
            if pass_results and i > 0:
                task.context["previous_step_result"] = results[-1].final_response if results else ""
            
            # Execute
            result = agent.execute(task)
            results.append(result)
            
            if result.status == AgentStatus.FAILED:
                # Stop pipeline on failure
                break
        
        return results

