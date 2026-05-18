import React, { useState } from 'react';
import { MessageSquare, X, Star, Send, CheckCircle, Loader2 } from 'lucide-react';
import { submitReview } from '../../services/api';

export default function ReviewModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [step, setStep] = useState('form'); // 'form' | 'success'
  const [reviewerName, setReviewerName] = useState('');
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const resetForm = () => {
    setReviewerName('');
    setRating(0);
    setHoverRating(0);
    setMessage('');
    setError(null);
    setStep('form');
  };

  const handleOpen = () => {
    resetForm();
    setIsOpen(true);
  };

  const handleClose = () => {
    setIsOpen(false);
    resetForm();
  };

  const handleSubmit = async () => {
    if (!message.trim()) {
      setError('Please enter your feedback.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await submitReview({
        reviewer_name: reviewerName.trim() || undefined,
        rating: rating > 0 ? rating : undefined,
        message: message.trim(),
      });
      setStep('success');
      setTimeout(() => {
        handleClose();
      }, 2500);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-105"
        title="Send feedback"
      >
        <MessageSquare size={18} />
        <span className="text-sm font-medium hidden sm:inline">Feedback</span>
      </button>

      {/* Modal overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={handleClose}>
          <div
            className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-800">
                {step === 'success' ? 'Sent!' : 'Send Feedback'}
              </h2>
              <button onClick={handleClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
                <X size={20} className="text-gray-400" />
              </button>
            </div>

            {step === 'success' ? (
              /* Success state */
              <div className="px-5 py-10 flex flex-col items-center text-center">
                <CheckCircle size={56} className="text-green-500 mb-4" />
                <p className="text-lg font-medium text-gray-800">Thank you!</p>
                <p className="text-sm text-gray-500 mt-1">Your feedback has been recorded.</p>
              </div>
            ) : (
              /* Form */
              <div className="px-5 py-4 space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">
                    Your Name <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    placeholder="e.g., John Doe"
                    maxLength={100}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {/* Star rating */}
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1.5">
                    Rating <span className="text-gray-400">(optional)</span>
                  </label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setRating(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        onMouseLeave={() => setHoverRating(0)}
                        className="p-0.5 transition-transform hover:scale-110"
                      >
                        <Star
                          size={28}
                          className={`transition-colors ${
                            (hoverRating || rating) >= star
                              ? 'fill-yellow-400 text-yellow-400'
                              : 'text-gray-300'
                          }`}
                        />
                      </button>
                    ))}
                    {rating > 0 && (
                      <span className="text-xs text-gray-400 ml-2 self-center">
                        {rating}/5
                      </span>
                    )}
                  </div>
                </div>

                {/* Message */}
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">
                    Feedback Message <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Share your experience with the app..."
                    rows={4}
                    maxLength={5000}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  />
                  <p className="text-xs text-gray-400 mt-1 text-right">{message.length}/5000</p>
                </div>

                {/* Error */}
                {error && (
                  <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  onClick={handleSubmit}
                  disabled={isSubmitting || !message.trim()}
                  className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium rounded-lg px-4 py-2.5 transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send size={16} />
                      Send Feedback
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}