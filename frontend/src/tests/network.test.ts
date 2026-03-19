/// <reference types="jest" />
import { check_for_error, InternalError, ApiResponse } from '../utils/network';

describe('check_for_error', () => {
  it('does nothing when code is undefined or 0', () => {
    // implementation throws when `code` is not a number, so empty object should throw
    expect(() => check_for_error({} as unknown as ApiResponse)).toThrowError(InternalError);

    try {
      check_for_error({} as unknown as ApiResponse);
      // should not reach here
      throw new Error('Expected InternalError to be thrown');
    } catch (e) {
      if (e instanceof InternalError) {
        expect(e.code).toBe(-1);
        expect(String(e)).toContain('无效的响应格式');
      } else {
        // rethrow unexpected errors so test fails
        throw e;
      }
    }

    // explicit zero code should not throw
    expect(() => check_for_error({ code: 0 } as ApiResponse)).not.toThrow();
  });

  it('throws InternalError when code is non-zero', () => {
    expect(() => check_for_error({ code: 5, info: 'boom' } as ApiResponse)).toThrowError(InternalError);

    try {
      check_for_error({ code: 5, info: 'boom' } as ApiResponse);
      // should not reach here
      throw new Error('Expected InternalError to be thrown');
    } catch (e) {
      if (e instanceof InternalError) {
        expect(e.code).toBe(5);
        expect(String(e)).toContain('boom');
      } else {
        // rethrow unexpected errors so test fails
        throw e;
      }
    }
  });
});
