import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import ItineraryPage from "./pages/itinerary/ItineraryPage";
import MainPage from "./pages/main/MainPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<MainPage />} />
          <Route path="/itinerary/:itineraryId" element={<ItineraryPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
