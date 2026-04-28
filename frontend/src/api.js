import axios from "axios";

const api = axios.create({
  baseURL: "https://war-app-r4ij.onrender.com",
});

export default api;