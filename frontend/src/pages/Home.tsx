import Header from "../components/Header";
import UrlForm from "../components/UrlForm";
import ProgressCard from "../components/ProgressCard";
import ClipList from "../components/ClipList";
import VerticalVideo from "../components/VerticalVideo";

function Home() {
  return (
    <div
      style={{
        maxWidth: "1000px",
        margin: "40px auto",
        padding: "20px",
        fontFamily: "Arial",
      }}
    >
      <Header />

      <UrlForm />

      <ProgressCard />

      <ClipList />

      <VerticalVideo />
    </div>
  );
}

export default Home;