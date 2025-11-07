import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Mic, MicOff, PhoneCall, PhoneOff, MessageSquare } from "lucide-react";
import { toast } from "sonner";

const VoiceBotPage = ({ api }) => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [testMessage, setTestMessage] = useState("");
  const [chatResponse, setChatResponse] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  
  const audioContextRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const dataChannelRef = useRef(null);
  const audioElementRef = useRef(null);

  // Fetch agents on mount
  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get(`${api}/agents`);
      setAgents(response.data);
      if (response.data.length > 0) {
        setSelectedAgent(response.data[0].id);
      }
    } catch (error) {
      console.error("Error fetching agents:", error);
      toast.error("Failed to load agents");
    }
  };

  const setupAudioElement = () => {
    if (!audioElementRef.current) {
      audioElementRef.current = document.createElement("audio");
      audioElementRef.current.autoplay = true;
      document.body.appendChild(audioElementRef.current);
    }

    peerConnectionRef.current.ontrack = (event) => {
      audioElementRef.current.srcObject = event.streams[0];
    };
  };

  const setupLocalAudio = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => {
        peerConnectionRef.current.addTrack(track, stream);
      });
    } catch (error) {
      console.error("Error accessing microphone:", error);
      toast.error("Failed to access microphone");
      throw error;
    }
  };

  const setupDataChannel = () => {
    dataChannelRef.current = peerConnectionRef.current.createDataChannel("oai-events");
    dataChannelRef.current.onmessage = (event) => {
      console.log("Received event:", event.data);
    };
  };

  const startVoiceCall = async () => {
    if (!selectedAgent) {
      toast.error("Please select an agent first");
      return;
    }

    try {
      setConnectionStatus("connecting");
      
      // Get session token from backend
      const tokenResponse = await axios.post(`${api}/realtime/session`, {}, {
        headers: { "Content-Type": "application/json" }
      });
      
      if (!tokenResponse.data.client_secret?.value) {
        throw new Error("Failed to get session token");
      }

      // Create WebRTC peer connection
      peerConnectionRef.current = new RTCPeerConnection();
      setupAudioElement();
      await setupLocalAudio();
      setupDataChannel();

      // Create and send offer
      const offer = await peerConnectionRef.current.createOffer();
      await peerConnectionRef.current.setLocalDescription(offer);

      // Send offer to backend and get answer
      const response = await axios.post(
        `${api}/realtime/negotiate`,
        offer.sdp,
        {
          headers: { "Content-Type": "application/sdp" }
        }
      );

      const answer = {
        type: "answer",
        sdp: response.data.sdp
      };

      await peerConnectionRef.current.setRemoteDescription(answer);
      
      setIsConnected(true);
      setConnectionStatus("connected");
      toast.success("Voice call connected!");
    } catch (error) {
      console.error("Failed to start voice call:", error);
      setConnectionStatus("error");
      toast.error("Failed to connect voice call");
    }
  };

  const endVoiceCall = () => {
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    if (dataChannelRef.current) {
      dataChannelRef.current.close();
      dataChannelRef.current = null;
    }
    if (audioElementRef.current) {
      audioElementRef.current.srcObject = null;
    }
    setIsConnected(false);
    setConnectionStatus("disconnected");
    toast.info("Voice call ended");
  };

  const toggleMute = () => {
    if (peerConnectionRef.current) {
      const senders = peerConnectionRef.current.getSenders();
      senders.forEach((sender) => {
        if (sender.track && sender.track.kind === "audio") {
          sender.track.enabled = isMuted;
        }
      });
      setIsMuted(!isMuted);
    }
  };

  const testWithText = async () => {
    if (!selectedAgent || !testMessage.trim()) {
      toast.error("Please select an agent and enter a message");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${api}/chat`, {
        agent_id: selectedAgent,
        message: testMessage
      });
      setChatResponse(response.data.response);
      toast.success("Response received!");
    } catch (error) {
      console.error("Error testing agent:", error);
      toast.error("Failed to get response");
    } finally {
      setIsLoading(false);
    }
  };

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "bg-green-500";
      case "connecting":
        return "bg-yellow-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-400";
    }
  };

  const currentAgent = agents.find(a => a.id === selectedAgent);

  return (
    <div className="min-h-screen p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-teal-600 to-purple-600 bg-clip-text text-transparent" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Outbound Voice Bot
          </h1>
          <p className="text-base text-gray-600" style={{ fontFamily: 'Inter, sans-serif' }}>
            Multi-agent voice bot with real-time communication
          </p>
        </div>

        {/* Agent Selection */}
        <Card data-testid="agent-selection-card" className="border-2 border-teal-200 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              <MessageSquare className="w-5 h-5 text-teal-600" />
              Select Agent
            </CardTitle>
            <CardDescription>Choose which agent to test</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Active Agent</label>
              <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                <SelectTrigger data-testid="agent-selector" className="w-full">
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id} data-testid={`agent-option-${agent.id}`}>
                      {agent.name} ({agent.language})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {currentAgent && (
              <div className="p-4 bg-teal-50 rounded-lg border border-teal-200" data-testid="agent-details">
                <h3 className="font-semibold text-teal-800 mb-2">{currentAgent.name}</h3>
                <p className="text-sm text-teal-700 mb-2">{currentAgent.description}</p>
                <div className="text-xs text-teal-600">
                  <span className="font-medium">Language:</span> {currentAgent.language.toUpperCase()}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Voice Controls */}
        <Card data-testid="voice-controls-card" className="border-2 border-purple-200 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              <PhoneCall className="w-5 h-5 text-purple-600" />
              Voice Call Controls
            </CardTitle>
            <CardDescription>Start or end voice call with the selected agent</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${getConnectionStatusColor()} animate-pulse`}></div>
              <span className="text-sm font-medium capitalize">{connectionStatus}</span>
            </div>

            <div className="flex flex-wrap gap-3">
              {!isConnected ? (
                <Button
                  data-testid="start-call-btn"
                  onClick={startVoiceCall}
                  className="bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-md hover:shadow-lg"
                  disabled={!selectedAgent}
                >
                  <PhoneCall className="w-4 h-4 mr-2" />
                  Start Voice Call
                </Button>
              ) : (
                <>
                  <Button
                    data-testid="end-call-btn"
                    onClick={endVoiceCall}
                    className="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-md hover:shadow-lg"
                  >
                    <PhoneOff className="w-4 h-4 mr-2" />
                    End Call
                  </Button>
                  <Button
                    data-testid="mute-btn"
                    onClick={toggleMute}
                    variant={isMuted ? "destructive" : "outline"}
                    className="px-6 py-2 rounded-full font-medium transition-all duration-200"
                  >
                    {isMuted ? <MicOff className="w-4 h-4 mr-2" /> : <Mic className="w-4 h-4 mr-2" />}
                    {isMuted ? "Unmute" : "Mute"}
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Text Testing */}
        <Card data-testid="text-testing-card" className="border-2 border-blue-200 shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              <MessageSquare className="w-5 h-5 text-blue-600" />
              Text Testing
            </CardTitle>
            <CardDescription>Test agent responses with text messages</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Test Message</label>
              <textarea
                data-testid="test-message-input"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="Type your message here..."
                className="w-full min-h-[100px] p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            <Button
              data-testid="send-test-message-btn"
              onClick={testWithText}
              disabled={isLoading || !selectedAgent}
              className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white px-6 py-2 rounded-full font-medium transition-all duration-200 shadow-md hover:shadow-lg"
            >
              {isLoading ? "Sending..." : "Send Message"}
            </Button>

            {chatResponse && (
              <div className="p-4 bg-blue-50 rounded-lg border border-blue-200" data-testid="chat-response">
                <h4 className="font-semibold text-blue-800 mb-2">Response:</h4>
                <p className="text-sm text-blue-900 whitespace-pre-wrap">{chatResponse}</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default VoiceBotPage;
