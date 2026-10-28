"use client"

import { createContext, useContext, useId, type InputHTMLAttributes, type ReactNode } from "react"

// Field errors from the last save, keyed by input name ("assets.0.amount").
export const ErrorsContext = createContext<Record<string, string>>({})

export const useFieldError = (name: string): string | undefined => useContext(ErrorsContext)[name]

// Enum values are PascalCase identifiers; most read fine split into words.
const LABELS: Record<string, string> = {
  CertificateOfDeposit: "Certificate of deposit",
  Open30Day: "30-day open account",
}
export const enumLabel = (value: string) =>
  LABELS[value] ?? value.replace(/([a-z])([A-Z])/g, "$1 $2")

type Value = string | number | null | undefined

const Wrapper = ({ label, hint, error, describedBy, className = "", children }: {
  label: string
  className?: string
  hint?: string
  error?: string
  describedBy: string
  children: ReactNode
}) => (
  <label className={`flex flex-col gap-1 ${className}`}>
    <span className="text-sm font-medium">{label}</span>
    {children}
    {error ? (
      <span id={describedBy} className="text-xs text-error">{error}</span>
    ) : hint ? (
      <span id={describedBy} className="text-xs opacity-70">{hint}</span>
    ) : null}
  </label>
)

type FieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "name" | "defaultValue"> & {
  name: string
  label: string
  defaultValue: Value
  hint?: string
  // className goes on the wrapper (the grid item); this one on the <input>.
  inputClassName?: string
}

export const Field = ({ name, label, defaultValue, hint, className, inputClassName = "", ...input }: FieldProps) => {
  const error = useFieldError(name)
  const id = useId()
  return (
    <Wrapper label={label} hint={hint} error={error} describedBy={id} className={className}>
      <input
        name={name}
        defaultValue={defaultValue ?? ""}
        className={`input w-full ${error ? "input-error" : ""} ${inputClassName}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? id : undefined}
        {...input}
      />
    </Wrapper>
  )
}

// Decimals stay strings end to end (see the action), so a text input rather
// than type="number".
export const MoneyField = (props: Omit<FieldProps, "type" | "inputMode">) => (
  <Field inputMode="decimal" placeholder="0.00" {...props} />
)

export const IntField = (props: Omit<FieldProps, "type">) => (
  <Field type="number" min={0} step={1} {...props} />
)

export const SelectField = ({ name, label, values, defaultValue, hint }: {
  name: string
  label: string
  values: ReadonlyArray<string>
  defaultValue: Value
  hint?: string
}) => {
  const error = useFieldError(name)
  const id = useId()
  return (
    <Wrapper label={label} hint={hint} error={error} describedBy={id}>
      <select
        name={name}
        defaultValue={defaultValue ?? ""}
        className={`select w-full ${error ? "select-error" : ""}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? id : undefined}
      >
        <option value="">—</option>
        {values.map((v) => <option key={v} value={v}>{enumLabel(v)}</option>)}
      </select>
    </Wrapper>
  )
}

export const Section = ({ title, description, children }: {
  title: string
  description?: string
  children: ReactNode
}) => (
  <fieldset className="rounded-box border border-base-300 p-6">
    <legend className="px-2 text-lg font-semibold">{title}</legend>
    {description && <p className="mb-4 text-sm opacity-70">{description}</p>}
    <div className="grid gap-4 md:grid-cols-2">{children}</div>
  </fieldset>
)
