import '../styles/Button.css'

function Button({ children, onClick, variant = 'primary', disabled = false, type = 'button' }) {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
      type={type}
    >
      {children}
    </button>
  )
}

export default Button

