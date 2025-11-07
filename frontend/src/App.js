import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import VoiceBotPage from "@/components/VoiceBotPage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<VoiceBotPage api={API} />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
