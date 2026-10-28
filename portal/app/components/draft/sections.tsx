"use client"

// One component per URLA section of the draft. Input names are the draft's
// field paths ("subjectProperty.city"), which the saveDraft action unflattens.

import type { components } from "@/app/lib/core/schema"
import {
  assetTypeValues,
  liabilityTypeValues,
  loanProgramValues,
  loanPurposeValues,
  occupancyValues,
  ownStatusValues,
} from "@/app/lib/core/schema"
import { Field, IntField, MoneyField, Section, SelectField } from "./fields"
import RowList from "./RowList"

type Draft = components["schemas"]["UrlaDraft-Output"]
type Asset = components["schemas"]["AssetDraft-Output"]
type Liability = components["schemas"]["LiabilityDraft-Output"]

export const BorrowerSection = ({ value }: { value: Draft["borrower"] }) => (
  <Section title="Personal information">
    <Field name="borrower.firstName" label="First name" defaultValue={value?.firstName} autoComplete="given-name" />
    <Field name="borrower.lastName" label="Last name" defaultValue={value?.lastName} autoComplete="family-name" />
    <Field name="borrower.dateOfBirth" label="Date of birth" type="date" defaultValue={value?.dateOfBirth} autoComplete="bday" />
    <Field name="borrower.phoneNumber" label="Phone" type="tel" defaultValue={value?.phoneNumber} autoComplete="tel" hint="US number" />
    <Field name="borrower.email" label="Email" type="email" defaultValue={value?.email} autoComplete="email" />
  </Section>
)

// Both address sections share these four fields.
const AddressFields = ({ prefix, value, autoComplete }: {
  prefix: string
  value: { streetAddress?: string | null; city?: string | null; state?: string | null; zipCode?: string | null } | undefined
  autoComplete: boolean
}) => {
  const ac = (token: string) => (autoComplete ? token : "off")
  return (
    <>
      <Field name={`${prefix}.streetAddress`} label="Street address" defaultValue={value?.streetAddress} autoComplete={ac("street-address")} className="md:col-span-2" />
      <Field name={`${prefix}.city`} label="City" defaultValue={value?.city} autoComplete={ac("address-level2")} />
      <div className="grid grid-cols-2 gap-4">
        <Field name={`${prefix}.state`} label="State" defaultValue={value?.state} maxLength={2} placeholder="CA" inputClassName="uppercase" autoComplete={ac("address-level1")} />
        <Field name={`${prefix}.zipCode`} label="ZIP code" defaultValue={value?.zipCode} inputMode="numeric" autoComplete={ac("postal-code")} />
      </div>
    </>
  )
}

export const CurrentAddressSection = ({ value }: { value: Draft["address"] }) => (
  <Section title="Current address">
    <AddressFields prefix="address" value={value} autoComplete />
    <SelectField name="address.ownStatus" label="Own or rent" values={ownStatusValues} defaultValue={value?.ownStatus} />
    <IntField name="address.monthsAtAddress" label="Months at this address" defaultValue={value?.monthsAtAddress} />
  </Section>
)

export const IncomeSection = ({ value }: { value: Draft["income"] }) => (
  <Section title="Employment and income" description="Your current employer.">
    <Field name="income.employerName" label="Employer" defaultValue={value?.employerName} autoComplete="organization" />
    <Field name="income.position" label="Position" defaultValue={value?.position} autoComplete="organization-title" />
    <Field name="income.startDate" label="Start date" type="date" defaultValue={value?.startDate} />
    <MoneyField name="income.monthlyIncome" label="Monthly income ($)" defaultValue={value?.monthlyIncome} />
  </Section>
)

export const AssetsSection = ({ value }: { value: Draft["assets"] }) => (
  <RowList<Asset>
    name="assets"
    title="Assets"
    description="Bank and investment accounts."
    itemLabel="Account"
    initial={value ?? []}
    renderRow={(prefix, row) => (
      <>
        <Field name={`${prefix}.institutionName`} label="Institution" defaultValue={row?.institutionName} />
        <SelectField name={`${prefix}.assetType`} label="Account type" values={assetTypeValues} defaultValue={row?.assetType} />
        <MoneyField name={`${prefix}.amount`} label="Balance ($)" defaultValue={row?.amount} />
      </>
    )}
  />
)

export const LiabilitiesSection = ({ value }: { value: Draft["liabilities"] }) => (
  <RowList<Liability>
    name="liabilities"
    title="Liabilities"
    description="Debts you owe: credit cards, car loans, leases."
    itemLabel="Debt"
    initial={value ?? []}
    renderRow={(prefix, row) => (
      <>
        <Field name={`${prefix}.institutionName`} label="Creditor" defaultValue={row?.institutionName} />
        <SelectField name={`${prefix}.liabilityType`} label="Type" values={liabilityTypeValues} defaultValue={row?.liabilityType} />
        <MoneyField name={`${prefix}.balance`} label="Unpaid balance ($)" defaultValue={row?.balance} />
        <MoneyField name={`${prefix}.monthlyAmount`} label="Monthly payment ($)" defaultValue={row?.monthlyAmount} />
        <IntField name={`${prefix}.monthsRemaining`} label="Months remaining" defaultValue={row?.monthsRemaining} hint="Required for installment loans" />
      </>
    )}
  />
)

export const LoanSection = ({ value }: { value: Draft["loan"] }) => (
  <Section title="Loan">
    <SelectField name="loan.loanPurpose" label="Purpose" values={loanPurposeValues} defaultValue={value?.loanPurpose} />
    <MoneyField name="loan.loanAmount" label="Loan amount ($)" defaultValue={value?.loanAmount} />
    <SelectField name="loan.loanProgram" label="Loan program" values={loanProgramValues} defaultValue={value?.loanProgram} />
    <IntField name="loan.loanTermMonths" label="Term (months)" defaultValue={value?.loanTermMonths} placeholder="360" />
  </Section>
)

export const PropertySection = ({ value }: { value: Draft["subjectProperty"] }) => (
  <Section
    title="Property"
    description="The home you're buying or refinancing. Leave the address empty if you haven't chosen one yet; a refinance needs it."
  >
    {/* Not the borrower's own address, so no browser autofill. */}
    <AddressFields prefix="subjectProperty" value={value} autoComplete={false} />
    <SelectField name="subjectProperty.occupancy" label="Occupancy" values={occupancyValues} defaultValue={value?.occupancy} />
    <MoneyField name="subjectProperty.propertyValue" label="Property value ($)" defaultValue={value?.propertyValue} />
    <MoneyField name="subjectProperty.monthlyTaxes" label="Monthly property taxes ($)" defaultValue={value?.monthlyTaxes} />
    <MoneyField name="subjectProperty.monthlyHoi" label="Monthly homeowner's insurance ($)" defaultValue={value?.monthlyHoi} />
  </Section>
)
