import { useJob } from "../context/JobContext";

function ContentPack() {
  const { status } = useJob();

  // NOTE: later we will connect contentPack state
  return (
    <div style={{ marginTop: 30 }}>
      <h3>Content Pack</h3>
      <p>Generated after clips detection</p>
    </div>
  );
}

export default ContentPack;