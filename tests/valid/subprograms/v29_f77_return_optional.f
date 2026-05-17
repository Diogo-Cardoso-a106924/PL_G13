program retopt
  integer z
  call noop()
  z = zeroval()
  print *, z
end

subroutine noop()
end

integer function zeroval()
  zeroval = 0
end
