// What this app stands for, and the shortcuts it takes.
const DemoNotice = () => (
  <div role="note" className="alert max-w-xl text-sm">
    <div className="flex flex-col gap-1">
      <p>
        <strong>Research prototype with synthetic data only.</strong>
      </p>
      <p>
        This app stands in for each lender&apos;s own origination system. It is
        separate from the borrower&apos;s service: it fetches applications with
        the lender&apos;s own credentials and keeps its own copies.
      </p>
      <p>
        There is no staff login, so anyone who can open this page can act as any
        demo lender.
      </p>
    </div>
  </div>
);

export default DemoNotice;
