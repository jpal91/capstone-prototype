"use client"

import { useRef, useState, type ReactNode } from "react"

import { MAX_ROWS } from "@/app/lib/draft"
import { GroupError } from "./fields"

type RowListProps<T> = {
  // Input names are `${name}.${index}.field`.
  name: string
  title: string
  description?: string
  itemLabel: string
  initial: T[]
  renderRow: (prefix: string, row: T | undefined) => ReactNode
}

// Inputs are uncontrolled: a stable key per row keeps what the user typed
// when an earlier row is removed, while the names are renumbered from the
// position so the action always gets indexes 0..n.
const RowList = <T,>({ name, title, description, itemLabel, initial, renderRow }: RowListProps<T>) => {
  const nextId = useRef(initial.length)
  // data is undefined for rows added in this session.
  const [rows, setRows] = useState<{ id: number; data: T | undefined }[]>(
    () => initial.map((data, id) => ({ id, data }))
  )

  const add = () => setRows((rs) => [...rs, { id: nextId.current++, data: undefined }])
  const remove = (id: number) => setRows((rs) => rs.filter((r) => r.id !== id))

  return (
    <fieldset className="rounded-box border border-base-300 p-6">
      <legend className="px-2 text-lg font-semibold">{title}</legend>
      {description && <p className="mb-4 text-sm opacity-70">{description}</p>}
      <GroupError name={name} />

      <div className="flex flex-col gap-4">
        {rows.length === 0 && <p className="text-sm opacity-70">None added.</p>}
        {rows.map((row, i) => (
          <div key={row.id} className="rounded-box bg-base-200 p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-medium">{itemLabel} {i + 1}</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => remove(row.id)}>
                Remove
              </button>
            </div>
            {/* core's cross-field rules report on the whole row. */}
            <GroupError name={`${name}.${i}`} />
            <div className="grid gap-4 md:grid-cols-2">{renderRow(`${name}.${i}`, row.data)}</div>
          </div>
        ))}

        <div>
          <button type="button" className="btn btn-sm" onClick={add} disabled={rows.length >= MAX_ROWS}>
            Add {itemLabel.toLowerCase()}
          </button>
          {rows.length >= MAX_ROWS && <span className="ml-2 text-xs opacity-70">Up to {MAX_ROWS}.</span>}
        </div>
      </div>
    </fieldset>
  )
}

export default RowList
