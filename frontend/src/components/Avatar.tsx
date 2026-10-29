export default function Avatar({ name, index }: { name: string; index: number }) {
  return (
    <span className="avatar" style={{ background: `hsl(${(index % 12) * 30} 65% 82%)` }}>
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}
