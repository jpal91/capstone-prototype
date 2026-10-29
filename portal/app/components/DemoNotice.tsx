// Shown before anyone signs in: what this is, and what it deliberately isn't.
const DemoNotice = ({ showAccounts = false }: { showAccounts?: boolean }) => (
  <div role="note" className="alert max-w-xl text-sm">
    <div className="flex flex-col gap-1">
      <p>
        <strong>Research prototype with synthetic data only.</strong> Don&apos;t
        enter real personal or financial information.
      </p>
      <p>
        This is a portable <em>pre-application</em>: it doesn&apos;t collect
        your Social Security number or demographic (HMDA) information. You give
        those directly to the lender you choose.
      </p>
      {showAccounts && (
        <p>
          Demo accounts: <code>alice</code> and <code>bob</code>. Their
          passwords are the defaults in <code>compose.yml</code>.
        </p>
      )}
    </div>
  </div>
);

export default DemoNotice;
