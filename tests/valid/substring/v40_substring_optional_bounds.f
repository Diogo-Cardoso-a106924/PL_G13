program sub_bounds
  character*6 a
  a = '123456'
  a(:3) = 'ABC'
  a(4:) = 'xyz'
  print *, a
end
