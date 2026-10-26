
type VersionCardProps = {
  sha256: string;
  createdAt: string;
}

const VersionCard = ({ sha256, createdAt }: VersionCardProps) => {
  return (
    <div
      className="w-md bg-base-100 rounded-xl py-4 flex justify-evenly"
    >
      <div className="flex flex-col">
        <div>
          <span>Version Hash: </span>
          <span className="text-mono">{sha256}</span>
        </div>
        <div>
          <span>Created At: </span>
          <span>{createdAt}</span>
        </div>
      </div>
      <button className="btn">Review</button>
    </div>
  )
}

export default VersionCard
